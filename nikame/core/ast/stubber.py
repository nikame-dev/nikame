import ast
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ParamStub:
    name: str
    type_hint: str | None = None
    default_value: str | None = None

    def to_repr(self) -> str:
        res = self.name
        if self.type_hint:
            res += f": {self.type_hint}"
        if self.default_value:
            res += f" = {self.default_value}"
        return res


@dataclass
class FunctionStub:
    name: str
    params: list[ParamStub] = field(default_factory=list)
    return_type: str | None = None
    is_async: bool = False
    docstring: str | None = None

    def to_repr(self) -> str:
        prefix = "async " if self.is_async else ""
        params_str = ", ".join(p.to_repr() for p in self.params)
        ret_str = f" -> {self.return_type}" if self.return_type else ""
        return f"{prefix}def {self.name}({params_str}){ret_str}: ..."


@dataclass
class ClassStub:
    name: str
    bases: list[str] = field(default_factory=list)
    methods: list[FunctionStub] = field(default_factory=list)
    docstring: str | None = None

    def to_repr(self) -> str:
        bases_str = f"({', '.join(self.bases)})" if self.bases else ""
        res = f"class {self.name}{bases_str}:"
        if not self.methods:
            res += " ..."
        else:
            for m in self.methods:
                res += f"\n    {m.to_repr()}"
        return res


@dataclass
class ModuleStub:
    imports: list[str] = field(default_factory=list)
    classes: list[ClassStub] = field(default_factory=list)
    functions: list[FunctionStub] = field(default_factory=list)

    def to_compact_repr(self) -> str:
        parts = []
        if self.imports:
            parts.append("\n".join(self.imports))
        
        for c in self.classes:
            parts.append(c.to_repr())
        for f in self.functions:
            parts.append(f.to_repr())
        return "\n\n".join(parts)


class StubGenerator(ast.NodeVisitor):
    def __init__(self) -> None:
        self.module = ModuleStub()
        self._current_class: ClassStub | None = None

    def visit_Import(self, node: ast.Import) -> None:
        self.module.imports.append(ast.unparse(node))

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        self.module.imports.append(ast.unparse(node))

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(ast.unparse(base))

        class_stub = ClassStub(name=node.name, bases=bases)
        self._current_class = class_stub
        
        # Visit children to find methods
        self.generic_visit(node)
        
        self.module.classes.append(class_stub)
        self._current_class = None

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._handle_function(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._handle_function(node, is_async=True)

    def _handle_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, is_async: bool) -> None:
        params = []
        
        # Handle arguments
        for arg in node.args.args:
            type_hint = ast.unparse(arg.annotation) if arg.annotation else None
            params.append(ParamStub(name=arg.arg, type_hint=type_hint))
            
        ret_type = ast.unparse(node.returns) if node.returns else None
        
        func_stub = FunctionStub(
            name=node.name,
            params=params,
            return_type=ret_type,
            is_async=is_async
        )
        
        if self._current_class:
            self._current_class.methods.append(func_stub)
        else:
            self.module.functions.append(func_stub)


def generate_stub(source_path: Path) -> str:
    """Generates a compact stub representation of a Python file."""
    try:
        content = source_path.read_text()
        tree = ast.parse(content)
        generator = StubGenerator()
        generator.visit(tree)
        return generator.module.to_compact_repr()
    except Exception as e:
        return f"# Error generating stub for {source_path.name}: {e}"
