from . import nodes


class ASTreePrinter(nodes.Visitor[None]):
    def __init__(self, indent: int):
        self._indent = indent
        self._current = 0

    def dent(self):
        self_ = self

        class Denture:
            __slots__ = ()

            def __enter__(self):
                self_._current += self_._indent

            def __exit__(self, *_):
                self_._current -= self_._indent

        return Denture()

    def p(self, msg: str):
        print(" " * self._current + msg)

    def visit_assign(self, stmt: nodes.Assign):
        self.p(stmt.op.lexeme)
        with self.dent():
            stmt.left.visit(self)
            stmt.right.visit(self)

    def visit_decl(self, stmt: nodes.Decl):
        self.p(stmt.name.lexeme)
        with self.dent():
            stmt.type.visit(self)

    def visit_fdecl(self, stmt: nodes.FDecl):
        self.p(stmt.free.lexeme + " " + stmt.name.lexeme)
        with self.dent():
            stmt.type.visit(self)

    def visit_methoddecl(self, stmt: nodes.MethodDecl):
        self.p(f"{stmt.name.lexeme}({len(stmt.params)})")
        with self.dent():
            self.p("RETURN")
            with self.dent():
                stmt.return_type.visit(self)
            self.p("PARAMS")
            with self.dent():
                for param in stmt.params:
                    param.visit(self)

    def visit_block(self, stmt: nodes.Block):
        self.p("BLOCK")
        with self.dent():
            for member in stmt.members:
                member.visit(self)

    def visit_method(self, stmt: nodes.Method):
        self.visit_methoddecl(stmt)
        with self.dent():
            stmt.body.visit(self)

    def visit_functiondecl(self, stmt: nodes.FunctionDecl):
        self.p("FREE")
        with self.dent():
            self.visit_methoddecl(stmt)

    def visit_function(self, stmt: nodes.Function):
        self.visit_functiondecl(stmt)
        with self.dent():
            stmt.body.visit(self)

    def visit_class(self, stmt: nodes.Class):
        self.p(f"CLASS[name={stmt.name.lexeme}]:")
        with self.dent():
            for member in stmt.members:
                member.visit(self)

    def visit_return(self, stmt: nodes.Return):
        self.p(f"RETURN")
        with self.dent():
            if stmt.expr is None:
                self.p("VOID")
            else:
                stmt.expr.visit(self)

    def visit_typealias(self, stmt: nodes.TypeAlias):
        self.p(f"ALIAS[name={stmt.name.lexeme}]")
        with self.dent():
            stmt.typ.visit(self)

    def visit_import(self, stmt: nodes.Import):
        self.p(f"IMPORT[{stmt.upcnt}]")
        with self.dent():
            self.p(".".join(pth.lexeme for pth in stmt.path))

    def visit_while(self, stmt: nodes.While):
        self.p("WHILE")
        with self.dent():
            stmt.cond.visit(self)
            stmt.body.visit(self)

    def visit_for(self, stmt: nodes.For):
        self.p(f"FOR[binding={stmt.bind.lexeme}]")
        with self.dent():
            stmt.body.visit(self)

    def visit_generic(self, stmt: nodes.Generic):
        params = tuple(t.lexeme for t in stmt.params)
        self.p(f"GENERIC[name={stmt.name.lexeme}, params={params}]")
        with self.dent():
            for member in stmt.members:
                member.visit(self)

    def visit_if(self, stmt: nodes.If):
        self.p("IF")
        with self.dent():
            stmt.cond.visit(self)
            stmt.body.visit(self)

    def visit_typededuce(self, expr: nodes.TypeDeduce):
        self.visit_typeauto(expr)
        with self.dent():
            expr.operand.visit(self)

    def visit_group(self, expr: nodes.Group):
        self.p(expr.op.lexeme)
        with self.dent():
            expr.operand.visit(self)

    def visit_posify(self, expr: nodes.Posify):
        self.p(expr.op.lexeme)
        with self.dent():
            expr.operand.visit(self)

    def visit_negate(self, expr: nodes.Negate):
        self.p(expr.op.lexeme)
        with self.dent():
            expr.operand.visit(self)

    def visit_not(self, expr: nodes.Not):
        self.p(expr.op.lexeme)
        with self.dent():
            expr.operand.visit(self)

    def visit_bitnot(self, expr: nodes.BitNot):
        self.p(expr.op.lexeme)
        with self.dent():
            expr.operand.visit(self)

    def visit_equal(self, expr: nodes.Equal):
        self.p(expr.op.lexeme)
        with self.dent():
            expr.left.visit(self)
            expr.right.visit(self)

    def visit_nequal(self, expr: nodes.NEqual):
        self.p(expr.op.lexeme)
        with self.dent():
            expr.left.visit(self)
            expr.right.visit(self)

    def visit_greate(self, expr: nodes.GreatE):
        self.p(expr.op.lexeme)
        with self.dent():
            expr.left.visit(self)
            expr.right.visit(self)

    def visit_greatt(self, expr: nodes.GreatT):
        self.p(expr.op.lexeme)
        with self.dent():
            expr.left.visit(self)
            expr.right.visit(self)

    def visit_lesse(self, expr: nodes.LessE):
        self.p(expr.op.lexeme)
        with self.dent():
            expr.left.visit(self)
            expr.right.visit(self)

    def visit_lesst(self, expr: nodes.LessT):
        self.p(expr.op.lexeme)
        with self.dent():
            expr.left.visit(self)
            expr.right.visit(self)

    def visit_and(self, expr: nodes.And):
        self.p(expr.op.lexeme)
        with self.dent():
            expr.left.visit(self)
            expr.right.visit(self)

    def visit_or(self, expr: nodes.Or):
        self.p(expr.op.lexeme)
        with self.dent():
            expr.left.visit(self)
            expr.right.visit(self)

    def visit_bitor(self, expr: nodes.BitOr):
        self.p(expr.op.lexeme)
        with self.dent():
            expr.left.visit(self)
            expr.right.visit(self)

    def visit_bitand(self, expr: nodes.BitAnd):
        self.p(expr.op.lexeme)
        with self.dent():
            expr.left.visit(self)
            expr.right.visit(self)

    def visit_add(self, expr: nodes.Add):
        self.p(expr.op.lexeme)
        with self.dent():
            expr.left.visit(self)
            expr.right.visit(self)

    def visit_subtract(self, expr: nodes.Subtract):
        self.p(expr.op.lexeme)
        with self.dent():
            expr.left.visit(self)
            expr.right.visit(self)

    def visit_multiply(self, expr: nodes.Multiply):
        self.p(expr.op.lexeme)
        with self.dent():
            expr.left.visit(self)
            expr.right.visit(self)

    def visit_is(self, expr: nodes.Is):
        self.p(expr.op.lexeme)
        with self.dent():
            expr.left.visit(self)
            expr.right.visit(self)

    def visit_isnot(self, expr: nodes.IsNot):
        self.p(expr.op.lexeme)
        with self.dent():
            expr.left.visit(self)
            expr.right.visit(self)

    def visit_divide(self, expr: nodes.Divide):
        self.p(expr.op.lexeme)
        with self.dent():
            expr.left.visit(self)
            expr.right.visit(self)

    def visit_call(self, expr: nodes.Call):
        self.p(expr.op.lexeme)
        with self.dent():
            expr.left.visit(self)
            for arg in expr.right:
                arg.visit(self)

    def visit_subscript(self, expr: nodes.Subscript):
        self.p(expr.op.lexeme)
        with self.dent():
            expr.left.visit(self)
            with self.dent():
                for arg in expr.right:
                    arg.visit(self)

    def visit_dot(self, expr: nodes.Dot):
        self.p(expr.op.lexeme)
        with self.dent():
            expr.left.visit(self)
            self.p(expr.right.lexeme)

    def visit_continue(self, stmt: nodes.Continue):
        self.p(stmt.keyword.lexeme.upper())

    def visit_break(self, stmt: nodes.Break):
        self.p(stmt.keyword.lexeme.upper())

    def visit_primary(self, expr: nodes.Primary):
        self.p(expr.value.lexeme)

    def visit_typeauto(self, expr: nodes.TypeAuto):
        self.p(expr.token.lexeme)

    def visit_typecall(self, expr: nodes.TypeCall):
        self.p(expr.token.lexeme)
        with self.dent():
            expr.generic.visit(self)
            for param in expr.params:
                param.visit(self)

    def visit_typemember(self, expr: nodes.TypeMember):
        self.p(expr.token.lexeme)
        with self.dent():
            expr.left.visit(self)
            self.p(expr.right.lexeme)

    def visit_typename(self, expr: nodes.TypeName):
        self.p(expr.token.lexeme)

    def visit_init(self, stmt: nodes.Init):
        self.p(":")
        with self.dent():
            stmt.left.visit(self)
            stmt.typ.visit(self)
            stmt.right.visit(self)

    def visit_fdeclinit(self, stmt: nodes.FDeclInit):
        self.p(f"FDECLINIT")
        with self.dent():
            self.p(stmt.name.lexeme)
            stmt.init.visit(self)

    def print(self, node: nodes.Node):
        node.visit(self)
