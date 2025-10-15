import os
import sys
import shutil
import time
import subprocess
from typing import Dict, List, Optional


def _ensure_cli_available(cmd: str = "ip_builder") -> bool:
    """Best-effort probe for ip_builder CLI on PATH. Returns True if invocable."""
    try:
        subprocess.run([cmd, "--help"], check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except FileNotFoundError:
        return False


class TemplateIP:
    """
    TemplateIP wraps an ip_builder task (prefixing + filelist generation) and
    exposes a simple API to:
      - build or rebuild the generated RTL bundle
      - get a UHDL VComponent from the generated filelist for a specific top

    Typical usage:
        ip = TemplateIP(
            name="axi_lite",
            filelist="path/to/src/filelist.f",
            prefix="NPU_",
            output_dir="build/deliver/axi_lite",
            env_var="AXI_LITE_DIR",
        )
        ip.build()                    # ensure prefixed RTL exists
        vc = ip.vcomponent(top="some_top", WIDTH=32)   # create UHDL VComponent
    """

    def __init__(
        self,
        name: str,
        *,
        src_dir: Optional[str] = None,
        filelist: Optional[str] = None,
        prefix: str,
        output_dir: Optional[str] = None,
        keep_prefix: bool = False,
        exclude_foundation_ip: bool = True,
        macro_yaml: Optional[str] = None,
        env_var: Optional[str] = None,
        make_unity_wrapper: bool = True,
        build_on_init: bool = True,
        build_force: bool = True,
    ) -> None:
        if not src_dir and not filelist:
            raise ValueError("Either src_dir or filelist must be provided")
        if src_dir and filelist:
            raise ValueError("Provide only one of src_dir or filelist")

        self.name = name
        self.src_dir = os.path.abspath(src_dir) if src_dir else None
        self.filelist = os.path.abspath(filelist) if filelist else None
        self.prefix = prefix
        self.keep_prefix = keep_prefix
        self.exclude_foundation_ip = exclude_foundation_ip
        self.macro_yaml = os.path.abspath(macro_yaml) if macro_yaml else None
        self.env_var = env_var  # environment variable name for filelist path entries
        self.make_unity_wrapper = make_unity_wrapper

        # Default output dir inside workspace build folder if not provided
        if output_dir is None:
            output_dir = os.path.join(os.getcwd(), "build", "deliver", name)
        self.output_dir = os.path.abspath(output_dir)

        # CLI name (can be overridden for testing via env)
        self._ipb_cmd = os.environ.get("IP_BUILDER_CLI", "ip_builder")

        # Optionally build immediately for ergonomic API
        # Default keeps previous behavior (no implicit build) unless build_on_init=True
        if build_on_init:
            # Swallow errors? No: if build is requested at init, surface failures
            self.build(force=build_force)

    # ---------- build lifecycle ----------

    @property
    def generated_filelist(self) -> str:
        """Path to generated filelist within output_dir."""
        return os.path.join(self.output_dir, f"{self.prefix}filelist.f")

    @property
    def expanded_filelist(self) -> str:
        """Path to the temporary expanded filelist with $ENV prefixes resolved.

        This file is created on demand by _write_expanded_filelist().
        """
        base = os.path.splitext(self.generated_filelist)[0]
        return base + ".expanded.f"

    @property
    def unity_wrapper(self) -> str:
        """Path to the unity wrapper file under output_dir."""
        return os.path.join(self.output_dir, f"{self.prefix}unity_wrapper.sv")

    def _latest_input_mtime(self) -> float:
        """Compute a coarse timestamp representing source freshness."""
        latest = 0.0
        if self.src_dir:
            for root, _dirs, files in os.walk(self.src_dir):
                for fn in files:
                    if fn.endswith((".sv", ".v", ".vh", ".svh", ".f")):
                        try:
                            m = os.path.getmtime(os.path.join(root, fn))
                            latest = max(latest, m)
                        except OSError:
                            pass
        elif self.filelist:
            try:
                latest = os.path.getmtime(self.filelist)
            except OSError:
                latest = 0.0
        if self.macro_yaml:
            try:
                latest = max(latest, os.path.getmtime(self.macro_yaml))
            except OSError:
                pass
        return latest

    def _output_mtime(self) -> float:
        try:
            return os.path.getmtime(self.generated_filelist)
        except OSError:
            return 0.0

    def needs_build(self) -> bool:
        """Return True if output is missing or older than inputs."""
        if not os.path.exists(self.output_dir):
            return True
        if not os.path.exists(self.generated_filelist):
            return True
        return self._output_mtime() < self._latest_input_mtime()

    def build(self, force: bool = False) -> str:
        """Run ip_builder to generate prefixed RTL into output_dir.

        Returns the path to the generated filelist.
        """
        if force or self.needs_build():
            if self.src_dir:
                # 1) run ip_builder in src-folder mode
                args = ["-s", self.src_dir, "-p", self.prefix, "-d", self.output_dir]
                if self.keep_prefix:
                    args.append("-k")
                if self.env_var:
                    args += ["-e", self.env_var]
                self._run_ip_builder(args)
                # 2) generate a filelist that indexes all generated SV/V files
                rel_files: List[str] = []
                for root, _dirs, files in os.walk(self.output_dir):
                    for fn in files:
                        if fn.endswith((".sv", ".v")):
                            abspath = os.path.join(root, fn)
                            rel = os.path.relpath(abspath, self.output_dir)
                            rel_files.append(rel)
                rel_files.sort()
                os.makedirs(self.output_dir, exist_ok=True)
                with open(self.generated_filelist, "w", encoding="utf-8") as f:
                    for rel in rel_files:
                        if self.env_var:
                            f.write(f"${self.env_var}/{rel}\n")
                        else:
                            f.write(rel + "\n")
            else:
                # filelist mode: ip_builder handles expansion and filelist emission
                args = ["-f", self.filelist, "-p", self.prefix, "-d", self.output_dir]
                if self.keep_prefix:
                    args.append("-k")
                if not self.exclude_foundation_ip:
                    args.append("-ne")
                if self.macro_yaml:
                    args += ["-m", self.macro_yaml]
                if self.env_var:
                    args += ["-e", self.env_var]
                self._run_ip_builder(args)
            # After any build, optionally produce helper artifacts
            #  - expanded .f with absolute paths
            #  - unity wrapper that includes all generated files
            self._write_expanded_filelist()
            if self.make_unity_wrapper:
                self._write_unity_wrapper()
        return self.generated_filelist

    def _write_expanded_filelist(self) -> str:
        """Create a filelist with any leading $ENV/ prefixes replaced by absolute paths.

        Many SystemVerilog tools don't expand $ENV variables inside .f files. Since
        ip_builder emits lines like "$ENV/path/to/file.sv", we produce a sibling
        filelist where these are rewritten to absolute paths under self.output_dir.
        Returns the path to the expanded filelist.
        """
        src_fl = self.generated_filelist
        dst_fl = self.expanded_filelist
        os.makedirs(self.output_dir, exist_ok=True)
        try:
            with open(src_fl, "r", encoding="utf-8") as fin, open(dst_fl, "w", encoding="utf-8") as fout:
                for raw in fin:
                    line = raw.strip()
                    if not line or line.startswith("#"):
                        continue
                    # Replace a leading $ENV/ prefix with output_dir joined path
                    if self.env_var and line.startswith(f"${self.env_var}/"):
                        rel = line[len(self.env_var) + 2 :]  # skip $ENV/
                        abspath = os.path.join(self.output_dir, rel)
                        fout.write(abspath + "\n")
                    elif line.startswith("$") and "/" in line:
                        # Generic $FOO/rel/path -> assume this bundle's output_dir
                        rel = line.split("/", 1)[1]
                        abspath = os.path.join(self.output_dir, rel)
                        fout.write(abspath + "\n")
                    else:
                        # Relative path from output_dir -> make absolute for robustness
                        if not os.path.isabs(line):
                            line = os.path.join(self.output_dir, line)
                        fout.write(line + "\n")
        except FileNotFoundError:
            # If original filelist missing, ensure build then retry once
            self.build()
            return self._write_expanded_filelist()
        return dst_fl

    def _write_unity_wrapper(self) -> str:
        """Create a single SystemVerilog wrapper that `include`s all generated files.

        The wrapper ensures all files are compiled as one compilation unit without
        requiring a compiler flag. The macro file (if present) is included first.
        Returns the path to the wrapper file.
        """
        self.build()
        files = self.get_generated_files()  # absolute paths
        if not files:
            raise RuntimeError("No generated files to include in unity wrapper")

        # Sort with macro file first if found
        macro_first: List[str] = []
        others: List[str] = []
        for p in files:
            base = os.path.basename(p)
            if base.endswith("_macros.sv") or base.endswith("macros.sv"):
                macro_first.append(p)
            else:
                others.append(p)
        ordered = macro_first + others

        wrapper_path = os.path.join(self.output_dir, f"{self.prefix}unity_wrapper.sv")
        with open(wrapper_path, "w", encoding="utf-8") as f:
            f.write("// Auto-generated by TemplateIP: unity wrapper to include all generated files\n")
            f.write("// DO NOT EDIT\n\n")
            # Prefer relative includes from output_dir so tools can resolve via --include-directory
            for p in ordered:
                try:
                    rel = os.path.relpath(p, self.output_dir)
                except Exception:
                    rel = p
                # Fallback to absolute if file escapes output_dir
                if rel.startswith(".."):
                    rel = p
                f.write(f"`include \"{rel}\"\n")
        return wrapper_path

    def _run_ip_builder(self, args: List[str]) -> None:
        """Run ip_builder via CLI, with fallback to repo-local script if needed."""
        # Try CLI first if present
        cli_ok = _ensure_cli_available(self._ipb_cmd)
        print(f"cmd: {[self._ipb_cmd] + args}")
        if cli_ok:
            try:
                subprocess.run([self._ipb_cmd] + args, check=True)
                return
            except subprocess.CalledProcessError as e:
                # proceed to fallback
                pass
        # Fallback: locate local ip_builder/ip_builder.py
        script = self._find_local_ip_builder()
        if not script:
            # If CLI existed but failed, re-raise; else give clear error
            if cli_ok:
                raise
            raise RuntimeError("Cannot locate ip_builder CLI or local script to run.")
        subprocess.run([sys.executable, script] + args, check=True)

    def _find_local_ip_builder(self) -> Optional[str]:
        """Search upwards for a repo-local ip_builder/ip_builder.py script."""
        here = os.path.dirname(os.path.abspath(__file__))
        for up in range(1, 8):
            root = os.path.abspath(os.path.join(here, *([".."] * up)))
            candidate = os.path.join(root, "ip_builder", "ip_builder.py")
            if os.path.isfile(candidate):
                return candidate
        # Also check CWD
        candidate = os.path.join(os.getcwd(), "ip_builder", "ip_builder.py")
        if os.path.isfile(candidate):
            return candidate
        return None

    def clean(self) -> None:
        """Remove the output_dir."""
        if os.path.isdir(self.output_dir):
            shutil.rmtree(self.output_dir)

    def get_generated_files(self) -> List[str]:
        """Return the list of generated files listed in the filelist.

        Paths are absolute (joined to output_dir) when env_var is used in filelist.
        """
        # Prefer the expanded filelist for consistent absolute paths
        self.build()
        fl = self._write_expanded_filelist()
        if not os.path.exists(fl):
            return []
        out: List[str] = []
        try:
            with open(fl, "r", encoding="utf-8") as f:
                for line in f:
                    p = line.strip()
                    if not p or p.startswith("#"):
                        continue
                    # Entries in expanded filelist are absolute; fall back to
                    # joining with output_dir if relative (defensive)
                    if not os.path.isabs(p):
                        p = os.path.join(self.output_dir, p)
                    out.append(p)
        except Exception:
            pass
        return out

    # ---------- VComponent factory ----------

    def vcomponent(
        self,
        *,
        top: str,
        instance: Optional[str] = None,
        slang_cmd: str = "slang",
        slang_opts: str = "--ignore-unknown-modules",
        struct_mode: str = "auto",
        preinclude: Optional[List[str]] = None,
        include_dirs: Optional[List[str]] = None,
        defines: Optional[Dict[str, str]] = None,
        combine_as_unity: Optional[bool] = None,
        **params: Dict,
    ):
        """Create a UHDL VComponent for a top module from the generated bundle.

        Ensures the bundle is built, sets up environment variable (if provided)
        so that any $ENV entries in the filelist are resolved by slang.
        """
        # Local import to avoid a hard dependency at module import time
        from .VComponent import VComponent

        # Ensure outputs exist; choose between unity wrapper or expanded filelist
        self.build()
        use_unity = self.make_unity_wrapper if combine_as_unity is None else bool(combine_as_unity)
        if use_unity and os.path.exists(self.unity_wrapper):
            source_for_slang = self.unity_wrapper
        elif use_unity:
            source_for_slang = self._write_unity_wrapper()
        else:
            source_for_slang = self._write_expanded_filelist()

        # Build extra slang options for convenience
        extra_opts_parts: List[str] = []
        if preinclude:
            for f in preinclude:
                extra_opts_parts += ["--preinclude", f]
        # If using unity wrapper, default include dir to the bundle output_dir
        if use_unity and not include_dirs:
            include_dirs = [self.output_dir]
        if include_dirs:
            for d in include_dirs:
                extra_opts_parts += ["--include-directory", d]
        if defines:
            for k, v in defines.items():
                extra_opts_parts += ["-D", f"{k}={v}"]
        combined_opts = slang_opts
        if extra_opts_parts:
            combined_opts = (slang_opts + " " + " ".join(extra_opts_parts)).strip()

        return VComponent(
            file=source_for_slang,
            top=top,
            instance=instance or top,
            slang_cmd=slang_cmd,
            slang_opts=combined_opts,
            struct_mode=struct_mode,
            **params,
        )

    # ---------- Convenience API ----------

    def get_vcomponent(
        self,
        *,
        top: str,
        instance: Optional[str] = None,
        slang_cmd: str = "slang",
        slang_opts: str = "--ignore-unknown-modules",
        struct_mode: str = "auto",
        include_dirs: Optional[List[str]] = None,
        defines: Optional[Dict[str, str]] = None,
        **params: Dict,
    ):
        """Convenience wrapper to obtain a UHDL VComponent from this TemplateIP.

        Defaults to using the unity wrapper (if enabled at construction) so that
        macros and directives are shared without requiring -single-unit.
        """
        return self.vcomponent(
            top=top,
            instance=instance,
            slang_cmd=slang_cmd,
            slang_opts=slang_opts,
            struct_mode=struct_mode,
            include_dirs=include_dirs,
            defines=defines,
            **params,
        )
