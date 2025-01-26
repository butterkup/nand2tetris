import enum
import typing as ty
from contextlib import contextmanager

from . import nodes
from .token import Token


class _MissingExpr(Exception): ...


class _S(enum.IntFlag):
    NONE = enum.auto()
    LOOP = enum.auto()
    METHOD = enum.auto()
    FUNCTION = enum.auto()


class _Ctx:
    def __init__(self, default: _S = _S.NONE):
        self.stats = [default]

    @contextmanager
    def ctx(self, scope: _S):
        self.stats.append(scope)
        yield
        self.stats.pop()

    def test(self, val: _S):
        return self.stats[-1] & val


class _Parser_helper:
    "LL(1) parser for Jack, too sensitive, do not change any state."

    def __init__(self, lexer: ty.Iterable[Token]):
        self.lexer = iter(lexer)
        self.current = next(self.lexer)
        self.status = _Ctx()

    def match(self, typ: Token.Type):
        if self.current.typ == typ:
            return self.consume()

    def report(
        self,
        err: str,
        sloc: Token.Loc | None = None,
        eloc: Token.Loc | None = None,
        *,
        ErrorT: type[BaseException] | None = None,
    ):
        sloc = self.current.start if sloc is None else sloc
        eloc = self.current.end if eloc is None else eloc
        ErrorT = Exception if ErrorT is None else ErrorT
        raise ErrorT(f"{sloc}-{eloc}: {err}")

    def consume(self) -> Token:
        current = self.current
        self.current = next(self.lexer)
        return current

    def expect(
        self,
        typ: Token.Type,
        err: str | None = None,
        sloc: Token.Loc | None = None,
        eloc: Token.Loc | None = None,
        *,
        ErrorT: type[BaseException] | None = None,
    ):
        tk = self.match(typ)
        if tk is None:
            err = f"Expected token {typ} but got {self.current}" if err is None else err
            self.report(err, sloc, eloc, ErrorT=ErrorT)
        return tk

    def expression(self) -> nodes.Expr:
        return self.expr_identity()

    def _expr_l2r(
        self,
        typ: Token.Type,
        higher: ty.Callable[[], nodes.Expr],
        ExprT: ty.Callable[[nodes.Expr, Token, nodes.Expr], nodes.Expr],
    ):
        left = higher()
        while tk := self.match(typ):
            right = higher()
            left = ExprT(left, tk, right)
        return left

    def expr_identity(self):
        left = self.expr_or()
        while True:
            NodeT: type[nodes._BinExpr]
            if op := self.match(Token.Type.IS):
                NodeT = nodes.Is
            elif op := self.match(Token.Type.ISNOT):
                NodeT = nodes.IsNot
            else:
                break
            right = self.expr_or()
            left = NodeT(left, op, right)
        return left

    def expr_or(self):
        return self._expr_l2r(Token.Type.OR, self.expr_and, nodes.Or)

    def expr_and(self):
        return self._expr_l2r(Token.Type.AND, self.expr_equality, nodes.And)

    def expr_equality(self):
        left = self.expr_bitor()
        while True:
            NodeT: type[nodes._BinExpr]
            if op := self.match(Token.Type.EQUAL):
                NodeT = nodes.Equal
            elif op := self.match(Token.Type.NEQUAL):
                NodeT = nodes.NEqual
            else:
                break
            right = self.expr_comparison()
            left = NodeT(left, op, right)
        return left

    def expr_comparison(self):
        left = self.expr_bitor()
        while True:
            NodeT: type[nodes._BinExpr]
            if op := self.match(Token.Type.GREATE):
                NodeT = nodes.GreatE
            elif op := self.match(Token.Type.GREATT):
                NodeT = nodes.GreatT
            elif op := self.match(Token.Type.LESSE):
                NodeT = nodes.LessE
            elif op := self.match(Token.Type.LESST):
                NodeT = nodes.LessT
            else:
                break
            right = self.expr_bitor()
            left = NodeT(left, op, right)
        return left

    def expr_bitor(self):
        return self._expr_l2r(Token.Type.BAR, self.expr_bitand, nodes.BitOr)

    def expr_bitand(self):
        return self._expr_l2r(Token.Type.AMP, self.expr_add, nodes.BitAnd)

    def expr_add(self):
        return self._expr_l2r(Token.Type.PLUS, self.expr_sub, nodes.Add)

    def expr_sub(self):
        return self._expr_l2r(Token.Type.MINUS, self.expr_mul, nodes.Subtract)

    def expr_mul(self):
        return self._expr_l2r(Token.Type.STAR, self.expr_div, nodes.Multiply)

    def expr_div(self):
        return self._expr_l2r(Token.Type.SLASH, self.expr_unary, nodes.Divide)

    def expr_unary(self):
        match self.current.typ:
            case Token.Type.MINUS:
                tk = self.consume()
                operand = self.expr_unary()
                return nodes.Negate(tk, operand)
            case Token.Type.PLUS:
                tk = self.consume()
                operand = self.expr_unary()
                return nodes.Posify(tk, operand)
            case Token.Type.NOT:
                tk = self.consume()
                operand = self.expr_unary()
                return nodes.Not(tk, operand)
            case Token.Type.TILDE:
                tk = self.consume()
                operand = self.expr_unary()
                return nodes.BitNot(tk, operand)
            case _:
                return self.expr_call()

    def _expr_comma_sep(self):
        exprs: list[nodes.Expr] = []
        while True:
            expr = self.expression()
            exprs.append(expr)
            if self.match(Token.Type.COMMA):
                continue
            break
        return exprs

    def expr_call(self):
        left = self.expr_dot()
        while True:
            if tk := self.match(Token.Type.LPAREN):
                arguments = (
                    list[nodes.Expr]()
                    if self.current.typ == Token.Type.RPAREN
                    else self._expr_comma_sep()
                )
                self.expect(
                    Token.Type.RPAREN, "Open paren '(' was never closed.", tk.start
                )
                left = nodes.Call(left, tk, arguments)
            elif tk := self.match(Token.Type.LBRACKET):
                arguments = (
                    list[nodes.Expr]()
                    if self.current.typ == Token.Type.RBRACKET
                    else self._expr_comma_sep()
                )
                self.expect(
                    Token.Type.RBRACKET, "Open bracket '[' was never closed.", tk.start
                )
                left = nodes.Subscript(left, tk, arguments)
            else:
                break
        return left

    def expr_dot(self):
        left = self.expr_group()
        while dot := self.match(Token.Type.DOT):
            right = self.expect(Token.Type.ID)
            left = nodes.Dot(left, dot, right)
        return left

    def expr_group(self):
        if tk := self.match(Token.Type.LPAREN):
            operand = self.expression()
            self.expect(Token.Type.RPAREN, "Open paren '(' was not closed.", tk.start)
            return nodes.Group(tk, operand)
        return self.expr_primary()

    def expr_primary(self):
        match self.current.typ:
            case (
                Token.Type.FALSE
                | Token.Type.TRUE
                | Token.Type.ID
                | Token.Type.STRING
                | Token.Type.INT
            ):
                pass
            case Token.Type.THIS:
                if not self.status.test(_S.METHOD):
                    self.report(f"'this' used outside a method: {self.current}")
            case _:
                self.report(
                    f"Expected an expression, but got {self.current.typ}",
                    ErrorT=_MissingExpr,
                )
        return nodes.Primary(self.consume())

    def _type_expression(self, left: nodes.TypeExpr):
        while True:
            if op := self.match(Token.Type.LBRACKET):
                params: list[nodes.TypeExpr] = []
                if self.current.typ != Token.Type.RBRACKET:
                    while True:
                        param = self.type_expression()
                        params.append(param)
                        if self.match(Token.Type.COMMA):
                            continue
                        break
                self.expect(
                    Token.Type.RBRACKET, "Open bracket '[' was not closed.", op.start
                )
                left = nodes.TypeCall(op, left, params)
            elif op := self.match(Token.Type.DOT):
                member = self.expect(Token.Type.ID)
                left = nodes.TypeMember(op, left, member)
                while op := self.match(Token.Type.DOT):
                    member = self.expect(Token.Type.ID)
                    left = nodes.TypeMember(op, left, member)
            else:
                return left

    def type_expression(self):
        if tk := self.match(Token.Type.AUTO):
            if p := self.match(Token.Type.LPAREN):
                expr = self.expression()
                self.expect(
                    Token.Type.RPAREN, "Open paren '(' was not closed.", p.start
                )
                return nodes.TypeDeduce(tk, expr)
            return nodes.TypeAuto(tk)
        typname = nodes.TypeName(self.expect(Token.Type.ID))
        right = self._type_expression(typname)
        return typname if right is None else right

    def _parse_decl(self) -> tuple[Token, nodes.TypeExpr]:
        name = self.expect(Token.Type.ID)
        self.expect(Token.Type.COLON)
        typ = self.type_expression()
        return name, typ

    def parse_decl(self) -> nodes.Decl:
        name, typ = self._parse_decl()
        return nodes.Decl(name, typ)

    def parse_fdecl(self, free: Token) -> nodes.FDecl:
        name, typ = self._parse_decl()
        if self.match(Token.Type.ASSIGN):
            init = self.expression()
            return nodes.FDeclInit(name, typ, free, init)
        return nodes.FDecl(name, typ, free)

    def parse_return(self):
        if not self.status.test(_S.METHOD | _S.FUNCTION):
            self.report("'return' used outside a function or method.")
        ret = self.expect(Token.Type.RETURN)
        if self.match(Token.Type.SCOLON):
            expr = None
        else:
            expr = self.expression()
            self.expect(Token.Type.SCOLON)
        return nodes.Return(ret, expr)

    def parse_assign(self):
        current = self.current
        try:
            store = self.expression()
        except _MissingExpr:
            if current is not self.current:
                raise
        else:
            if tk := self.match(Token.Type.COLON):
                if not (
                    isinstance(store, nodes.Primary)
                    and store.value.typ == Token.Type.ID
                ):
                    self.report(
                        "Only ID expressions can be declared. Expected ID before ':'",
                        current.start,
                        tk.start,
                    )
                typ = self.type_expression()
                if tk := self.match(Token.Type.ASSIGN):
                    value = self.expression()
                    return nodes.Init(store, tk, value, typ)
                self.report("Variables must be initialized on declarations")
            if tk := self.match(Token.Type.ASSIGN):
                match store:
                    case nodes.Subscript() | nodes.Dot():
                        pass
                    case nodes.Primary(value=Token(typ=typ, lexeme=lx)):
                        if typ != Token.Type.ID:
                            self.report(f"Literal {lx!r} is not assignable.")
                    case _:
                        self.report(
                            f"Cannot assign to expression {store.__class__.__name__!r}"
                        )
                value = self.expression()
                return nodes.Assign(store, tk, value)
            return store

    def parse_block(self):
        brace = self.expect(Token.Type.LBRACE)
        stmts: list[nodes.Node] = []
        while True:
            match self.current.typ:
                case Token.Type.IF:
                    stmt = self.parse_if()
                case Token.Type.WHILE:
                    stmt = self.parse_while()
                case Token.Type.RETURN:
                    stmt = self.parse_return()
                case Token.Type.FOR:
                    stmt = self.parse_for()
                case Token.Type.LBRACE:
                    stmt = self.parse_block()
                case Token.Type.CONTINUE:
                    if not self.status.test(_S.LOOP):
                        self.report("'continue' used outside a loop")
                    stmt = nodes.Continue(self.consume())
                    self.expect(Token.Type.SCOLON)
                case Token.Type.BREAK:
                    if not self.status.test(_S.LOOP):
                        self.report("'break' used outside a loop")
                    stmt = nodes.Break(self.consume())
                    self.expect(Token.Type.SCOLON)
                case Token.Type.SCOLON:
                    self.consume()
                    continue
                case Token.Type.RBRACE:
                    break
                case _:
                    stmt = self.parse_assign()
                    if stmt is None:
                        self.report(f"Unexpected token {self.current}")
                    self.expect(Token.Type.SCOLON)
            stmts.append(stmt)
        self.expect(Token.Type.RBRACE, "Open brace '{' was never closed.", brace.start)
        return nodes.Block(brace, stmts)

    def parse_if(self):
        if_ = self.expect(Token.Type.IF)
        cond = self.expression()
        body = self.parse_block()
        else_ = None
        if tk := self.match(Token.Type.ELSE):
            else_body = self.parse_block()
            else_ = tk, else_body
        return nodes.If(if_, cond, body, else_)

    def parse_while(self):
        while_ = self.expect(Token.Type.WHILE)
        cond = self.expression()
        with self.status.ctx(_S.LOOP):
            body = self.parse_block()
        return nodes.While(while_, cond, body)

    def parse_for(self):
        for_ = self.expect(Token.Type.FOR)
        name = self.expect(Token.Type.ID)
        self.expect(Token.Type.ASSIGN)
        iterable = self.expression()
        with self.status.ctx(_S.LOOP):
            body = self.parse_block()
        return nodes.For(for_, name, iterable, body)

    def parse_proc_decl(self):
        name = self.expect(Token.Type.ID)
        self.expect(Token.Type.LPAREN)
        params: list[nodes.Decl] = []
        if self.current.typ != Token.Type.RPAREN:
            seen = set[str]()
            while True:
                param = self.parse_decl()
                if param.name.lexeme in seen:
                    self.report(
                        f"Duplicate parameter '{param.name.lexeme}' declaration."
                    )
                seen.add(param.name.lexeme)
                params.append(param)
                if self.match(Token.Type.COMMA):
                    continue
                break
        self.expect(Token.Type.RPAREN)
        self.expect(Token.Type.COLON)
        rettype = self.type_expression()
        return name, params, rettype

    def parse_proc(self, fn: Token, free: Token | None):
        with self.status.ctx(_S.METHOD if free is None else _S.FUNCTION):
            name, params, rettype = self.parse_proc_decl()
            match self.current.typ:
                case Token.Type.LBRACE:
                    body = self.parse_block()
                    if free is None:
                        return nodes.Method(fn, name, params, rettype, body)
                    return nodes.Function(fn, name, params, rettype, free, body)
                case Token.Type.SCOLON:
                    if free is None:
                        return nodes.MethodDecl(fn, name, params, rettype)
                    return nodes.FunctionDecl(fn, name, params, rettype, free)
                case _:
                    self.report(f"Expected '{{' or ';' but got {self.current.lexeme!r}")

    def parse_class_body(self):
        self.expect(Token.Type.LBRACE)
        members: nodes.Class.Members = []
        seen = set[str]()
        while True:
            match self.current.typ:
                case Token.Type.FREE:
                    free = self.consume()
                    if name := self.match(Token.Type.ID):
                        self.expect(Token.Type.COLON)
                        typ = self.type_expression()
                        self.expect(Token.Type.SCOLON)
                        decl = nodes.FDecl(name, typ, free)
                        members.append(decl)
                        name = decl.name
                    elif fn := self.match(Token.Type.FN):
                        func = self.parse_proc(fn, free)
                        members.append(func)
                        name = func.name
                    else:
                        self.report(f"Expected ID or 'fn', but got {self.current}")
                case Token.Type.FN:
                    func = self.parse_proc(self.consume(), None)
                    members.append(func)
                    name = func.name
                case Token.Type.ID:
                    decl = self.parse_decl()
                    self.expect(Token.Type.SCOLON)
                    members.append(decl)
                    name = decl.name
                case Token.Type.RBRACE:
                    self.consume()
                    break
                case Token.Type.SCOLON:
                    continue
                case Token.Type.USING:
                    stmt = self.parse_using()
                    members.append(stmt)
                    name = (
                        stmt.path[-1] if isinstance(stmt, nodes.Import) else stmt.name
                    )
                case _:
                    self.report(f"Unexpected token {self.current}")
            if name.lexeme in seen:
                self.report(f"Symbol {name.lexeme!r} redeclared in class scope.")
            seen.add(name.lexeme)
        return members

    def _parse_using_path(self, part: Token | None = None) -> tuple[list[Token], int]:
        path: list[Token] = [] if part is None else [part]
        upcnt: int = 0
        if part is None:
            while self.match(Token.Type.DOT):
                upcnt += 1
            upcnt = upcnt - 1 if upcnt else upcnt
        while True:
            part = self.expect(Token.Type.ID)
            path.append(part)
            if self.match(Token.Type.DOT):
                continue
            break
        if not path:
            self.report("Missing import target.")
        return path, upcnt

    def parse_using(self):
        using = self.expect(Token.Type.USING)
        match self.current.typ:
            case Token.Type.DOT:
                path, upcnt = self._parse_using_path()
                stmt = nodes.Import(using, path, upcnt)
            case Token.Type.ID:
                name = self.consume()
                if self.match(Token.Type.DOT):
                    path, upcnt = self._parse_using_path(name)
                    stmt = nodes.Import(using, path, upcnt)
                elif self.match(Token.Type.ASSIGN):
                    value = self.type_expression()
                    stmt = nodes.TypeAlias(using, name, value)
                else:
                    stmt = nodes.Import(using, [name], 0)
            case _:
                self.report("Expected ID or '.' after keyword 'using'")
        self.expect(Token.Type.SCOLON)
        return stmt

    def parse_class(self):
        klass = self.expect(Token.Type.CLASS)
        name = self.expect(Token.Type.ID)
        if self.match(Token.Type.LBRACKET):
            type_params: list[Token] = []
            while True:
                param = self.expect(Token.Type.ID)
                type_params.append(param)
                if self.match(Token.Type.COMMA):
                    continue
                break
            self.expect(Token.Type.RBRACKET)
            body = self.parse_class_body()
            return nodes.Generic(klass, name, body, type_params)
        body = self.parse_class_body()
        return nodes.Class(klass, name, body)

    def parse(self):
        while True:
            match self.current.typ:
                case Token.Type.USING:
                    return self.parse_using()
                case Token.Type.CLASS:
                    return self.parse_class()
                case Token.Type.SCOLON:
                    pass
                case Token.Type.EOT:
                    break
                case _:
                    self.report(f"Unexpected token {self.current}")


def Parser(lexer: ty.Iterable[Token]) -> ty.Generator[nodes.Node, None, None]:
    "LL(1) parser for Jack. EOT must be the last token in the Token Stream (lexer)"
    parser = _Parser_helper(lexer)
    while True:
        node = parser.parse()
        if node is None:
            break
        yield node
