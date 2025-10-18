import os
import sys
import shutil
import time
import subprocess
from typing import Dict, List, Optional

# Import VComponent for TemplateComponent inheritance
from .VComponent import VComponent


def _ensure_cli_available(cmd: str = "ip_builder") -> bool:
    """Best-effort probe for ip_builder CLI on PATH. Returns True if invocable."""
    try:
        subprocess.run([cmd, "--help"], check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except FileNotFoundError:
        return False


class TemplateComponent(VComponent):
    """
    TemplateComponent extends VComponent with a reference to its parent TemplateIP.
    
    This allows components created from TemplateIP to track which template they came from,
    enabling features like automatic rebuild detection and template-aware operations.
    
    The component inherits all VComponent functionality and adds template-specific metadata.
    """
    
    def __init__(self, parent_template: 'TemplateIP', *args, **kwargs) -> None:
        """
        Create a TemplateComponent for a specific TemplateIP.
        
        Args:
            parent_template: The TemplateIP that generated this component
            *args, **kwargs: Arguments passed to VComponent.__init__
        """
        # Initialize the VComponent base class
        super().__init__(*args, **kwargs)
        
        # Add template-specific attribute
        self._parent_template = parent_template
    
    @property
    def parent_template(self) -> 'TemplateIP':
        """Get the parent TemplateIP that generated this component."""
        return self._parent_template
    
    def _create_this_vfile(self, path):
        """
        Override _create_this_vfile to trigger TemplateIP build when component generation happens.
        
        This method is called by Component.generate_verilog() -> _create_all_vfile() chain.
        It triggers the parent TemplateIP to build the RTL files into a subdirectory named
        after the template to avoid conflicts with parent component verilog files.
        
        Args:
            path: The base output directory (e.g., "build/gen")
                  The actual build will go to path/{template_name}/ (e.g., "build/gen/npu_dti/")
        """
        # Build to a subdirectory named after the template to avoid overwriting parent files
        template_output_dir = os.path.join(path, self._parent_template.name)
        self._parent_template.build_for_generate_verilog(template_output_dir)
    
    def generate_verilog(self, iteration=False):
        """
        Override generate_verilog to trigger TemplateIP build with correct parameters.
        
        When a top-level component calls generate_verilog, this ensures that all
        TemplateComponents in the hierarchy trigger their parent TemplateIP to build
        into the same output directory with:
          - exclude_foundation_ip=True
          - make_unity_wrapper=False
        
        The TemplateIP tracks builds per output_dir to ensure only one build happens
        even when multiple components from the same template are in the hierarchy.
        
        Args:
            iteration: If True, recursively generate verilog for all sub-components
        """
        # Trigger build for this component's template
        # Use the parent component's output_path as the build directory
        if hasattr(self, 'output_path') and self.output_path:
            output_dir = self.output_path
        else:
            # Fallback to current working directory if no output_path set
            output_dir = os.getcwd()
        
        # Request build from parent template
        # This will only actually build once per output_dir due to internal tracking
        self._parent_template.build_for_generate_verilog(output_dir)
        
        # Call parent generate_verilog (VComponent version)
        # VComponent doesn't generate files, it's a wrapper, so this is a no-op
        # But we call it for consistency and potential future extensions
        if iteration:
            # Recursively trigger generate_verilog for sub-components
            for comp in getattr(self, 'component_list', []):
                comp.generate_verilog(iteration=True)
    
    def __repr__(self) -> str:
        return f"TemplateComponent(template={self._parent_template.name}, module={getattr(self, '_module_name', 'unknown')})"


class TemplateIP:
    """
    TemplateIP wraps an ip_builder task (prefixing + filelist generation) and
    exposes a simple API to:
      - build or rebuild the generated RTL bundle
      - get a UHDL VComponent from the generated filelist for a specific top

    TemplateIP instances are automatically managed as singletons by name.
    Creating a TemplateIP with the same name twice will return the existing instance.

    Typical usage:
        # Define the template (no build yet)
        ip = TemplateIP(
            name="axi_lite",
            filelist="path/to/src/filelist.f",
            prefix="NPU_",
            env_var="AXI_LITE_DIR",
        )
        
        # Build with custom parameters
        ip.build(
            output_dir="build/deliver/axi_lite",
            exclude_foundation_ip=True,
            make_unity_wrapper=True
        )
        
        # Or use defaults (output_dir=build/deliver/{name}, exclude_foundation_ip=True, make_unity_wrapper=True)
        ip.build()
        
        # Get VComponent
        vc = ip.vcomponent(top="some_top", WIDTH=32)
        
        # Creating with same name returns the same instance
        ip2 = TemplateIP(name="axi_lite", filelist="...", prefix="NPU_")
        assert ip is ip2  # True - singleton by name
        
    Note:
        Build-time parameters (output_dir, exclude_foundation_ip, make_unity_wrapper)
        are specified when calling build(), not during instantiation.
        This allows the same TemplateIP to be built with different configurations.
    """
    
    _instances: Dict[str, 'TemplateIP'] = {}

    def __new__(
        cls,
        name: str,
        *,
        src_dir: Optional[str] = None,
        filelist: Optional[str] = None,
        prefix: Optional[str] = None,
        keep_prefix: bool = False,
        macro_yaml: Optional[str] = None,
        env_var: Optional[str] = None,
    ):
        """
        Create a new TemplateIP or return existing instance with the same name.
        
        This implements the singleton pattern per name, managed automatically
        in the background without requiring explicit manager calls.
        """
        # Check if instance already exists
        if name in cls._instances:
            return cls._instances[name]
        
        # Create new instance
        instance = super().__new__(cls)
        cls._instances[name] = instance
        
        # Mark that this instance needs initialization
        instance._initialized = False
        
        return instance

    def __init__(
        self,
        name: str,
        *,
        src_dir: Optional[str] = None,
        filelist: Optional[str] = None,
        prefix: Optional[str] = None,
        keep_prefix: bool = False,
        macro_yaml: Optional[str] = None,
        env_var: Optional[str] = None,
    ) -> None:
        # Skip initialization if already initialized (singleton reuse)
        if self._initialized:
            return
        
        # Validate parameters only for new instances
        if not src_dir and not filelist:
            raise ValueError("Either src_dir or filelist must be provided")
        if src_dir and filelist:
            raise ValueError("Provide only one of src_dir or filelist")
        if prefix is None:
            raise ValueError("prefix must be provided")

        self.name = name
        self.src_dir = os.path.abspath(src_dir) if src_dir else None
        self.filelist = os.path.abspath(filelist) if filelist else None
        self.prefix = prefix
        self.keep_prefix = keep_prefix
        self.macro_yaml = os.path.abspath(macro_yaml) if macro_yaml else None
        self.env_var = env_var  # environment variable name for filelist path entries

        # Build-time parameters (set during build())
        self._output_dir: Optional[str] = None
        self._exclude_foundation_ip: bool = True  # default
        self._make_unity_wrapper: bool = True     # default
        
        # Build state tracking for get_component
        self._component_build_completed: bool = False  # Tracks if built with correct params for components
        self._component_output_dir: Optional[str] = None  # Remembers where the component build was done
        
        # Build state tracking for generate_verilog
        # Dictionary to track which output directories have been built for generate_verilog
        # Key: absolute output directory path, Value: True if built
        self._verilog_build_dirs: Dict[str, bool] = {}

        # CLI name (can be overridden for testing via env)
        self._ipb_cmd = os.environ.get("IP_BUILDER_CLI", "ip_builder")

        # Mark as initialized
        self._initialized = True
    
    @property
    def output_dir(self) -> str:
        """Get the output directory. Defaults to build/deliver/{name} if not set."""
        if self._output_dir is None:
            return os.path.join(os.getcwd(), "build", "deliver", self.name)
        return self._output_dir
    
    def set_output_dir(self, output_dir: str) -> None:
        """Set a custom output directory for build artifacts."""
        self._output_dir = os.path.abspath(output_dir)

    # ---------- singleton management ----------
    
    @classmethod
    def get_instance(cls, name: str) -> Optional['TemplateIP']:
        """
        Get an existing TemplateIP instance by name without creating a new one.
        
        Args:
            name: Name of the TemplateIP to retrieve
            
        Returns:
            TemplateIP instance if found, None otherwise
        """
        return cls._instances.get(name)
    
    @classmethod
    def has_instance(cls, name: str) -> bool:
        """Check if a TemplateIP instance with the given name exists."""
        return name in cls._instances
    
    @classmethod
    def clear_instance(cls, name: str) -> bool:
        """
        Remove a TemplateIP instance from the singleton registry.
        
        Args:
            name: Name of the TemplateIP to remove
            
        Returns:
            True if the instance was removed, False if it didn't exist
        """
        if name in cls._instances:
            del cls._instances[name]
            return True
        return False
    
    @classmethod
    def clear_all_instances(cls) -> None:
        """Remove all TemplateIP instances from the singleton registry."""
        cls._instances.clear()
    
    @classmethod
    def list_instances(cls) -> List[str]:
        """Get a list of all registered TemplateIP instance names."""
        return list(cls._instances.keys())

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

    def build(
        self,
        output_dir: Optional[str] = None,
        exclude_foundation_ip: Optional[bool] = None,
        make_unity_wrapper: Optional[bool] = None,
    ) -> str:
        """Run ip_builder to generate prefixed RTL into output_dir.

        Args:
            output_dir: Custom output directory for this build. If not provided,
                       uses the default or previously set output_dir.
            exclude_foundation_ip: Whether to exclude foundation IP files when building.
                                  Default is True (excludes foundation IP).
            make_unity_wrapper: Whether to generate a unity wrapper file that includes
                               all generated files. Default is True.

        Returns:
            The path to the generated filelist.
        
        Note:
            Build is always executed when called. There is no automatic check
            for whether build is needed. You control when to build manually.
        """
        # Update build-time parameters if provided
        if output_dir is not None:
            self.set_output_dir(output_dir)
        if exclude_foundation_ip is not None:
            self._exclude_foundation_ip = exclude_foundation_ip
        if make_unity_wrapper is not None:
            self._make_unity_wrapper = make_unity_wrapper
        
        # Always build when called (no automatic freshness checking)
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
            if not self._exclude_foundation_ip:
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
        if self._make_unity_wrapper:
            self._write_unity_wrapper()
        
        # Track if this build is suitable for get_component
        # (requires exclude_foundation_ip=False and make_unity_wrapper=True)
        if not self._exclude_foundation_ip and self._make_unity_wrapper:
            self._component_build_completed = True
            self._component_output_dir = self.output_dir  # Remember where component files are
        else:
            self._component_build_completed = False
        
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
            # If original filelist missing, cannot expand (should call build() first)
            raise RuntimeError(
                f"Generated filelist not found: {src_fl}. "
                "Please ensure build() has been called successfully."
            )
        return dst_fl

    def _write_unity_wrapper(self) -> str:
        """Create a single SystemVerilog wrapper that `include`s all generated files.

        The wrapper ensures all files are compiled as one compilation unit without
        requiring a compiler flag. The macro file (if present) is included first.
        Returns the path to the wrapper file.
        
        Note: This method should only be called after build() has completed.
        """
        # Get list of generated files from expanded filelist
        fl = self.expanded_filelist
        if not os.path.exists(fl):
            raise RuntimeError(
                f"Expanded filelist not found: {fl}. "
                "This method should only be called after build() completes."
            )
        
        files: List[str] = []
        try:
            with open(fl, "r", encoding="utf-8") as f:
                for line in f:
                    p = line.strip()
                    if not p or p.startswith("#"):
                        continue
                    if not os.path.isabs(p):
                        p = os.path.join(self.output_dir, p)
                    files.append(p)
        except Exception:
            pass
        
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
    
    def build_for_generate_verilog(self, output_dir: str) -> None:
        """
        Build the template for generate_verilog phase with specific parameters.
        
        This method is called by TemplateComponent.generate_verilog() to ensure
        the RTL files are available in the target output directory. It uses:
          - exclude_foundation_ip=True (don't include foundation IP in output)
          - make_unity_wrapper=False (no unity wrapper needed for separate files)
        
        The method tracks builds per output_dir, so if multiple TemplateComponents
        from the same TemplateIP are in a hierarchy, only one build happens per
        output directory.
        
        Args:
            output_dir: The directory where generated files should be placed
        """
        # Normalize the output directory path
        abs_output_dir = os.path.abspath(output_dir)
        
        # Check if we've already built to this directory
        if abs_output_dir in self._verilog_build_dirs:
            # Already built to this directory, skip
            return
        
        # Mark this directory as being built (before actual build to prevent recursion)
        self._verilog_build_dirs[abs_output_dir] = True
        
        # Perform the build with generate_verilog-specific parameters
        self.build(
            output_dir=abs_output_dir,
            exclude_foundation_ip=True,
            make_unity_wrapper=False
        )

    def get_generated_files(self) -> List[str]:
        """Return the list of generated files listed in the filelist.

        Paths are absolute (joined to output_dir) when env_var is used in filelist.
        
        Note: build() should be called before this method to ensure files exist.
        """
        # Use the expanded filelist for consistent absolute paths
        fl = self.expanded_filelist
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

    # ---------- TemplateComponent factory ----------

    def get_component(
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
    ) -> TemplateComponent:
        """Get a TemplateComponent for a top module from the generated bundle.
        
        This method automatically ensures the TemplateIP has been built with the
        correct parameters (exclude_foundation_ip=False, make_unity_wrapper=True)
        before creating the component. If not already built with these parameters,
        it will trigger a build automatically.

        Args:
            top: Name of the top module to create a component for
            instance: Instance name (defaults to top name)
            slang_cmd: Command to invoke slang (default: "slang")
            slang_opts: Additional options for slang
            struct_mode: Structure parsing mode ("auto", "packed", "unpacked")
            include_dirs: Additional include directories for slang
            defines: Macro definitions to pass to slang
            **params: Module parameters to pass to slang (-G flags)

        Returns:
            TemplateComponent wrapping the VComponent with parent template reference
        
        Note:
            This method requires that the TemplateIP has been built with:
            - exclude_foundation_ip=False (to include all dependencies)
            - make_unity_wrapper=True (to create single compilation unit)
            
            If not already built with these parameters, a build will be triggered
            automatically using the default output_dir.
        """
        # Check if we need to build for component generation
        if not self._component_build_completed:
            # Build with required parameters for components
            # Use default output_dir to avoid conflicts with custom builds
            default_output_dir = os.path.join(os.getcwd(), "build", "deliver", self.name)
            self.build(
                output_dir=default_output_dir,
                exclude_foundation_ip=False,
                make_unity_wrapper=True
            )
        
        # Use the saved component output directory instead of current output_dir
        # This allows different builds (e.g., release builds) without affecting components
        component_output_dir = self._component_output_dir or self.output_dir
        unity_wrapper_path = os.path.join(component_output_dir, f"{self.prefix}unity_wrapper.sv")

        # Always use unity wrapper for components
        if not os.path.exists(unity_wrapper_path):
            raise RuntimeError(
                f"Unity wrapper not found: {unity_wrapper_path}. "
                "This should have been created by build()."
            )
        
        source_for_slang = unity_wrapper_path

        # Build slang options
        extra_opts_parts: List[str] = []
        
        # Default include dir to the component build output_dir for unity wrapper
        if not include_dirs:
            include_dirs = [component_output_dir]
        
        if include_dirs:
            for d in include_dirs:
                extra_opts_parts += ["--include-directory", d]
        
        if defines:
            for k, v in defines.items():
                extra_opts_parts += ["-D", f"{k}={v}"]
        
        combined_opts = slang_opts
        if extra_opts_parts:
            combined_opts = (slang_opts + " " + " ".join(extra_opts_parts)).strip()

        # Create TemplateComponent (which inherits from VComponent)
        return TemplateComponent(
            parent_template=self,
            file=source_for_slang,
            top=top,
            instance=instance or top,
            slang_cmd=slang_cmd,
            slang_opts=combined_opts,
            struct_mode=struct_mode,
            **params,
        )


class TemplateManager:
    """
    TemplateManager provides singleton management for TemplateIP instances.
    
    Each TemplateIP is uniquely identified by its name. When requesting a
    TemplateIP with the same name, the manager returns the existing instance
    instead of creating a new one.
    
    Usage:
        manager = TemplateManager()
        
        # First call creates a new TemplateIP instance
        ip1 = manager.get_or_create(
            name="axi_lite",
            filelist="path/to/filelist.f",
            prefix="NPU_",
        )
        
        # Second call with same name returns the existing instance
        ip2 = manager.get_or_create(name="axi_lite")
        assert ip1 is ip2  # True - same instance
        
        # Or use the global singleton manager
        ip = TemplateManager.get_global().get_or_create(name="axi_lite", ...)
    """
    
    _global_instance: Optional['TemplateManager'] = None
    
    def __init__(self) -> None:
        """Initialize a new TemplateManager with an empty registry."""
        self._registry: Dict[str, TemplateIP] = {}
    
    @classmethod
    def get_global(cls) -> 'TemplateManager':
        """Get or create the global singleton TemplateManager instance."""
        if cls._global_instance is None:
            cls._global_instance = cls()
        return cls._global_instance
    
    def get_or_create(
        self,
        name: str,
        *,
        src_dir: Optional[str] = None,
        filelist: Optional[str] = None,
        prefix: Optional[str] = None,
        keep_prefix: bool = False,
        macro_yaml: Optional[str] = None,
        env_var: Optional[str] = None,
    ) -> TemplateIP:
        """
        Get existing TemplateIP by name, or create a new one if not found.
        
        Args:
            name: Unique identifier for the TemplateIP instance
            **kwargs: Parameters for TemplateIP constructor (used only if creating new)
        
        Returns:
            TemplateIP instance associated with the given name
        
        Note:
            If a TemplateIP with the given name already exists, the additional
            parameters are ignored and the existing instance is returned.
            To update an existing instance, call unregister() first.
            
            Build-time parameters (output_dir, exclude_foundation_ip, make_unity_wrapper)
            should be specified when calling ip.build().
        """
        if name in self._registry:
            return self._registry[name]
        
        # Create new TemplateIP instance
        if prefix is None:
            raise ValueError(f"prefix is required when creating a new TemplateIP for '{name}'")
        
        ip = TemplateIP(
            name=name,
            src_dir=src_dir,
            filelist=filelist,
            prefix=prefix,
            keep_prefix=keep_prefix,
            macro_yaml=macro_yaml,
            env_var=env_var,
        )
        
        self._registry[name] = ip
        return ip
    
    def get(self, name: str) -> Optional[TemplateIP]:
        """
        Get an existing TemplateIP by name.
        
        Args:
            name: Name of the TemplateIP to retrieve
        
        Returns:
            TemplateIP instance if found, None otherwise
        """
        return self._registry.get(name)
    
    def has(self, name: str) -> bool:
        """Check if a TemplateIP with the given name exists."""
        return name in self._registry
    
    def unregister(self, name: str) -> bool:
        """
        Remove a TemplateIP from the registry.
        
        Args:
            name: Name of the TemplateIP to remove
        
        Returns:
            True if the TemplateIP was removed, False if it didn't exist
        """
        if name in self._registry:
            del self._registry[name]
            return True
        return False
    
    def clear(self) -> None:
        """Remove all TemplateIP instances from the registry."""
        self._registry.clear()
    
    def list_names(self) -> List[str]:
        """Get a list of all registered TemplateIP names."""
        return list(self._registry.keys())


# Convenience function for accessing the global manager
def get_template_ip(
    name: str,
    *,
    src_dir: Optional[str] = None,
    filelist: Optional[str] = None,
    prefix: Optional[str] = None,
    keep_prefix: bool = False,
    macro_yaml: Optional[str] = None,
    env_var: Optional[str] = None,
) -> TemplateIP:
    """
    Convenience function to get or create a TemplateIP using the global manager.
    
    This is equivalent to:
        TemplateManager.get_global().get_or_create(name, ...)
    
    Example:
        # First call creates the instance
        ip = get_template_ip(name="axi_lite", filelist="...", prefix="NPU_")
        
        # Subsequent calls return the same instance
        ip_again = get_template_ip(name="axi_lite")
        assert ip is ip_again
        
        # Specify build-time parameters when building
        ip.build(
            output_dir="custom/path",
            exclude_foundation_ip=True,
            make_unity_wrapper=True
        )
    """
    return TemplateManager.get_global().get_or_create(
        name=name,
        src_dir=src_dir,
        filelist=filelist,
        prefix=prefix,
        keep_prefix=keep_prefix,
        macro_yaml=macro_yaml,
        env_var=env_var,
    )
