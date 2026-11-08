// libuhdl_slang: the part of slang that UHDL needs, behind a small C interface.
//
// Every query takes a slang command line (the same syntax as the `slang` tool, starting with a
// program name) and returns a UTF-8 JSON document allocated with malloc. The caller releases it
// with uhdl_slang_free(). Nothing is written to disk. Python loads the library with ctypes, so
// the library does not depend on the Python version.
//
//   uhdl_slang_module(cmdline, path)    ports, parameters and type parameters of one instance
//   uhdl_slang_package(cmdline, name)   packed-struct typedefs and parameters of a package
//   uhdl_slang_check(cmdline)           full elaboration; diagnostics as slang prints them
//
// The JSON describes types recursively:
//   {"w": width, "s": signed, "alias": "pkg::name" | null, "k": "scalar" | "struct" | "union"
//    | "enum" | "unpacked", "fields": [{"n": name, "t": type}], "values": [[name, int]],
//    "elem": type, "left": int, "right": int}
// and every document has "ok" plus "error" when ok is false.

#include <cstdlib>
#include <cstring>
#include <memory>
#include <sstream>
#include <string>
#include <string_view>

#include "slang/ast/Compilation.h"
#include "slang/ast/Scope.h"
#include "slang/ast/Symbol.h"
#include "slang/ast/symbols/CompilationUnitSymbols.h"
#include "slang/ast/symbols/InstanceSymbols.h"
#include "slang/ast/symbols/MemberSymbols.h"
#include "slang/ast/symbols/ParameterSymbols.h"
#include "slang/ast/symbols/PortSymbols.h"
#include "slang/ast/symbols/VariableSymbols.h"
#include "slang/ast/types/AllTypes.h"
#include "slang/ast/types/Type.h"
#include "slang/diagnostics/DiagnosticEngine.h"
#include "slang/driver/Driver.h"
#include "slang/numeric/ConstantValue.h"

#define UHDL_API extern "C" __attribute__((visibility("default")))

using namespace slang;
using namespace slang::ast;

namespace {

constexpr const char* VERSION = "uhdl_slang 1 (slang 10.0)";

// ---------------------------------------------------------------- JSON output
struct Json {
    std::string s;
    void str(std::string_view v) {
        s += '"';
        for (unsigned char c : v) {
            switch (c) {
                case '"': s += "\\\""; break;
                case '\\': s += "\\\\"; break;
                case '\n': s += "\\n"; break;
                case '\r': s += "\\r"; break;
                case '\t': s += "\\t"; break;
                default:
                    if (c < 0x20) {
                        char buf[8];
                        snprintf(buf, sizeof buf, "\\u%04x", c);
                        s += buf;
                    }
                    else {
                        s += char(c);
                    }
            }
        }
        s += '"';
    }
    void key(std::string_view k) { str(k); s += ':'; }
    void raw(std::string_view v) { s += v; }
    void num(long long v) { s += std::to_string(v); }
    void boolean(bool v) { s += v ? "true" : "false"; }
};

char* finish(const std::string& text) {
    char* out = static_cast<char*>(std::malloc(text.size() + 1));
    if (out)
        std::memcpy(out, text.c_str(), text.size() + 1);
    return out;
}

char* error_doc(std::string_view msg) {
    Json j;
    j.raw("{\"ok\":false,\"error\":");
    j.str(msg);
    j.raw("}");
    return finish(j.s);
}

// ---------------------------------------------------------------- elaboration
struct Session {
    driver::Driver driver;
    std::unique_ptr<Compilation> compilation;
};

// Parse a slang command line and elaborate. Returns an error message, or empty on success.
std::string elaborate(Session& ses, const char* cmdline) {
    ses.driver.addStandardArgs();
    if (!ses.driver.parseCommandLine(std::string_view(cmdline)))
        return std::string("slang could not parse the command line: ") + cmdline;
    (void)ses.driver.processOptions();   // as the pyslang-based reader did: problems show as diagnostics
    (void)ses.driver.parseAllSources();
    ses.compilation = ses.driver.createCompilation();
    ses.compilation->getRoot();
    return {};
}

// pyslang's str(ConstantValue) is toString() with the default arguments
std::string cv_text(const ConstantValue& v) { return v.toString(); }

bool cv_int(const ConstantValue& v, long long& out) {
    if (!v.isInteger())
        return false;
    const SVInt& i = v.integer();
    if (i.hasUnknown())
        return false;
    auto x = i.as<int64_t>();
    if (!x)
        return false;
    out = *x;
    return true;
}

void type_json(Json& j, const Type& t, int depth = 0) {
    const Type& c = t.getCanonicalType();
    j.raw("{");
    j.key("w");
    j.num(t.getBitWidth());
    j.raw(",");
    j.key("s");
    j.boolean(t.isSigned());
    j.raw(",");
    j.key("alias");
    if (t.isAlias())
        j.str(t.getHierarchicalPath());
    else
        j.raw("null");
    j.raw(",");
    j.key("k");
    if (depth > 64) {                       // guard against pathological nesting
        j.str("scalar");
        j.raw("}");
        return;
    }
    if (c.isEnum()) {
        j.str("enum");
        j.raw(",");
        j.key("values");
        j.raw("[");
        bool first = true;
        for (auto& ev : c.as<EnumType>().values()) {
            if (!first)
                j.raw(",");
            first = false;
            long long v = 0;
            cv_int(ev.getValue(), v);
            j.raw("[");
            j.str(ev.name);
            j.raw(",");
            j.num(v);
            j.raw("]");
        }
        j.raw("]");
    }
    else if (c.isPackedUnion() || c.isStruct()) {
        j.str(c.isPackedUnion() ? "union" : "struct");
        j.raw(",");
        j.key("fields");
        j.raw("[");
        bool first = true;
        for (auto& f : c.as<Scope>().membersOfType<FieldSymbol>()) {
            if (!first)
                j.raw(",");
            first = false;
            j.raw("{");
            j.key("n");
            j.str(f.name);
            j.raw(",");
            j.key("t");
            type_json(j, f.getType(), depth + 1);
            j.raw("}");
        }
        j.raw("]");
    }
    else if (c.isUnpackedArray()) {
        j.str("unpacked");
        auto el = t.getArrayElementType();
        j.raw(",");
        j.key("elem");
        if (el)
            type_json(j, *el, depth + 1);
        else
            j.raw("null");
        if (c.hasFixedRange()) {
            auto r = t.getFixedRange();
            j.raw(",");
            j.key("left");
            j.num(r.left);
            j.raw(",");
            j.key("right");
            j.num(r.right);
        }
    }
    else {
        j.str("scalar");
    }
    j.raw("}");
}

const char* dir_name(ArgumentDirection d) {
    switch (d) {
        case ArgumentDirection::In: return "In";
        case ArgumentDirection::Out: return "Out";
        case ArgumentDirection::InOut: return "InOut";
        case ArgumentDirection::Ref: return "Ref";
    }
    return "InOut";
}

const InstanceSymbol* find_instance(Compilation& comp, std::string_view path) {
    auto& root = comp.getRoot();
    auto dot = path.find('.');
    std::string_view head = path.substr(0, dot);
    const InstanceSymbol* inst = nullptr;
    for (auto t : root.topInstances)
        if (t->name == head)
            inst = t;
    if (!inst && dot == std::string_view::npos && root.topInstances.size() == 1)
        inst = root.topInstances[0];       // a single top is used whatever its name
    if (!inst || dot == std::string_view::npos)
        return inst;
    std::string_view child = path.substr(dot + 1);
    for (auto& m : inst->body.membersOfType<InstanceSymbol>())
        if (m.name == child)
            return &m;
    return nullptr;
}

} // namespace

UHDL_API const char* uhdl_slang_version() { return VERSION; }

UHDL_API void uhdl_slang_free(char* p) { std::free(p); }

UHDL_API char* uhdl_slang_module(const char* cmdline, const char* path) {
    try {
        Session ses;
        auto err = elaborate(ses, cmdline);
        if (!err.empty())
            return error_doc(err);
        auto inst = find_instance(*ses.compilation, path);
        if (!inst)
            return error_doc(std::string("Top instance '") + path + "' not found in compilation");
        Json j;
        j.raw("{\"ok\":true,\"name\":");
        j.str(inst->name);
        j.raw(",\"members\":[");
        bool first = true;
        for (auto& m : inst->body.members()) {
            const char* kind = nullptr;
            if (m.kind == SymbolKind::Port)
                kind = "port";
            else if (m.kind == SymbolKind::Parameter)
                kind = "param";
            else if (m.kind == SymbolKind::TypeParameter)
                kind = "type_param";
            if (!kind)
                continue;
            if (!first)
                j.raw(",");
            first = false;
            j.raw("{");
            j.key("kind");
            j.str(kind);
            j.raw(",");
            j.key("name");
            j.str(m.name);
            if (m.kind == SymbolKind::Port) {
                auto& p = m.as<PortSymbol>();
                j.raw(",");
                j.key("dir");
                j.str(dir_name(p.direction));
                j.raw(",");
                j.key("type");
                type_json(j, p.getType());
            }
            else if (m.kind == SymbolKind::Parameter) {
                auto& p = m.as<ParameterSymbol>();
                j.raw(",");
                j.key("local");
                j.boolean(p.isLocalParam());
                j.raw(",");
                j.key("value");
                j.str(cv_text(p.getValue()));
            }
            j.raw("}");
        }
        j.raw("]}");
        return finish(j.s);
    }
    catch (const std::exception& e) {
        return error_doc(std::string("slang failed: ") + e.what());
    }
    catch (...) {
        return error_doc("slang failed with an unknown exception");
    }
}

UHDL_API char* uhdl_slang_package(const char* cmdline, const char* name) {
    try {
        Session ses;
        auto err = elaborate(ses, cmdline);
        if (!err.empty())
            return error_doc(err);
        auto pk = ses.compilation->getPackage(name);
        if (!pk)
            return error_doc(std::string("package ") + name + " not found");
        Json j;
        j.raw("{\"ok\":true,\"typedefs\":[");
        bool first = true;
        for (auto& m : pk->members()) {
            if (m.kind != SymbolKind::TypeAlias)
                continue;
            auto& alias = m.as<TypeAliasType>();
            if (!first)
                j.raw(",");
            first = false;
            j.raw("{");
            j.key("name");
            j.str(m.name);
            j.raw(",");
            j.key("type");
            type_json(j, alias.targetType.getType());
            j.raw("}");
        }
        j.raw("],\"params\":[");
        first = true;
        for (auto& m : pk->members()) {
            if (m.kind != SymbolKind::Parameter)
                continue;
            auto& p = m.as<ParameterSymbol>();
            if (!first)
                j.raw(",");
            first = false;
            j.raw("{");
            j.key("name");
            j.str(m.name);
            j.raw(",");
            j.key("text");
            j.str(cv_text(p.getValue()));
            long long v;
            if (cv_int(p.getValue(), v)) {
                j.raw(",");
                j.key("int");
                j.num(v);
            }
            j.raw("}");
        }
        j.raw("]}");
        return finish(j.s);
    }
    catch (const std::exception& e) {
        return error_doc(std::string("slang failed: ") + e.what());
    }
    catch (...) {
        return error_doc("slang failed with an unknown exception");
    }
}

UHDL_API char* uhdl_slang_check(const char* cmdline) {
    try {
        Session ses;
        auto err = elaborate(ses, cmdline);
        if (!err.empty())
            return error_doc(err);
        auto diags = ses.compilation->getAllDiagnostics();
        size_t errors = 0;
        for (auto& d : diags)
            if (d.isError())
                errors++;
        Json j;
        j.raw("{\"ok\":true,\"errors\":");
        j.num((long long)errors);
        j.raw(",\"report\":");
        j.str(DiagnosticEngine::reportAll(ses.driver.sourceManager, diags));
        j.raw("}");
        return finish(j.s);
    }
    catch (const std::exception& e) {
        return error_doc(std::string("slang failed: ") + e.what());
    }
    catch (...) {
        return error_doc("slang failed with an unknown exception");
    }
}
