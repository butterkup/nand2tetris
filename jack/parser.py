import enum
import typing as ty
from contextlib import contextmanager

from . import nodes
from .token import Token


class _MissingExpr(Exception):
    ...


class _S(enum.IntFlag):
    NONE = enum.auto()
    LOOP = enum.auto()
    FUNCTION = enum.auto()


class _Ctx:
    def __init__(self, default: _S = _S.NONE):
        self._settings = [default]

    @contextmanager
    def push(self, scope: _S):
        self._settings.append(scope)
        yield
        self._settings.pop()

    def test(self, val: _S):
        return self._settings[-1] & val


class _Parser_helper:
    "LL(1) parser for Jack, too sensitive, do not change any state."

    def __init__(self, lexer: ty.Iterable[Token]):
        self.lexer = iter(lexer)
        self.current = next(self.lexer)
        self.ctx = _Ctx()
        self.offset: int = 0
        self._declared = [set()]

    @property
    def declared(self) -> set[str]:
        return self._declared[-1]

    @contextmanager
    def scope(self, scope: set[str] | None = None):
        self._declared.append(scope or set())
        yield
        self._declared.pop()

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
        return self.expr_or()

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
        left = self.expr_group()
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
            elif tk := self.match(Token.Type.DOT):
                left = nodes.Dot(left, tk, self.expect(Token.Type.ID))
            else:
                break
        return left

    def expr_group(self):
        if tk := self.match(Token.Type.LPAREN):
            operand = self.expression()
            self.expect(Token.Type.RPAREN,
                        "Open paren '(' was not closed.", tk.start)
            return nodes.Group(tk, operand)
        return self.expr_primary()

    def expr_primary(self):
        match self.current.typ:
            case (
                Token.Type.FALSE
                | Token.Type.TRUE
                | Token.Type.STRING
                | Token.Type.INT
                | Token.Type.NIL
            ):
                pass
            case Token.Type.ID:
                value = self.consume()
                if tk := self.match(Token.Type.SCOPE):
                    path = [value.lexeme, self.expect(Token.Type.ID).lexeme]
                    while self.match(Token.Type.SCOPE):
                        path.append(self.expect(Token.Type.ID).lexeme)
                    return nodes.Scope(tk, path)
                return nodes.Identifier(value)
            case _:
                self.report(
                    f"Expected an expression, but got {self.current.typ}",
                    ErrorT=_MissingExpr,
                )
        return nodes.Primary(self.consume())

    def parse_decl(self) -> nodes.Decl:
        name = self.expect(Token.Type.ID)
        self.expect(Token.Type.COLON)
        typ = self.type_expression()
        return nodes.Decl(name, typ)

    def parse_return(self):
        if not self.ctx.test(_S.FUNCTION):
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
                if not isinstance(store, nodes.Identifier):
                    self.report(
                        "Only ID expressions can be declared. Expected ID before ':'",
                        current.start,
                        tk.start,
                    )
                self.declare(store.name)
                typ = self.type_expression()
                if tk := self.match(Token.Type.ASSIGN):
                    value = self.expression()
                    return nodes.Init(store, tk, typ, value)
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
                            f"Cannot assign to expression of type {store.__class__.__name__!r}"
                        )
                value = self.expression()
                return nodes.Assign(store, tk, value)
            return nodes.Expression(store)

    def _parse_block(self):
        brace = self.expect(Token.Type.LBRACE)
        stmts: list[nodes.Node] = []
        while not self.match(Token.Type.RBRACE):
            stmt = self.parse()
            if stmt is None:
                break
            stmts.append(stmt)
        return nodes.Block(brace, stmts)

    def parse_block(self):
        with self.scope():
            return self._parse_block()

    def parse_if(self):
        if_ = self.expect(Token.Type.IF)
        cond = self.expression()
        body = self.parse_block()
        els = self._parse_block() if self.match(Token.Type.ELSE) else None
        return nodes.If(if_, cond, body, els)

    def parse_while(self):
        while_ = self.expect(Token.Type.WHILE)
        cond = self.expression()
        with self.ctx.push(_S.LOOP):
            body = self.parse_block()
        return nodes.While(while_, cond, body)

    def parse_for(self):
        for_ = self.expect(Token.Type.FOR)
        name = self.expect(Token.Type.ID)
        self.expect(Token.Type.ASSIGN)
        iterable = self.expression()
        with self.ctx.push(_S.LOOP):
            body = self.parse_block()
        return nodes.For(for_, name, iterable, body)

    def parse_proc_decl(self):
        params: list[nodes.Decl] = []
        seen = set[str]()
        name = self.expect(Token.Type.ID)
        self.expect(Token.Type.LPAREN)
        while not self.match(Token.Type.RPAREN):
            param = self.parse_decl()
            if param.name.lexeme in seen:
                self.report(
                    f"Duplicate parameter '{param.name.lexeme}' declaration.")
            seen.add(param.name.lexeme)
            params.append(param)
            if not self.match(Token.Type.COMMA):
                self.expect(Token.Type.RPAREN)
                break
        self.expect(Token.Type.COLON)
        rettype = self.type_expression()
        return name, params, rettype, seen

    def parse_proc(self):
        fn = self.expect(Token.Type.FN)
        with self.ctx.push(_S.FUNCTION):
            name, params, rettype, seen = self.parse_proc_decl()
            match self.current.typ:
                case Token.Type.LBRACE:
                    with self.scope(seen):
                        body = self._parse_block()
                    return nodes.Function(fn, name, params, rettype, body)
                case Token.Type.SCOLON:
                    return nodes.FunctionDecl(fn, name, params, rettype)
                case _:
                    self.report(
                        f"Expected '{{' or ';' but got {self.current.lexeme!r}")

    def _parse_struct_body(self):
        self.expect(Token.Type.LBRACE)
        members: list[nodes.Decl] = []
        while not self.match(Token.Type.RBRACE):
            decl = self.parse_decl()
            members.append(decl)
            if not self.match(Token.Type.COMMA):
                self.expect(Token.Type.RBRACE)
                break
        return members

    def type_expression(self):
        value = self.expression()
        if isinstance(value, (nodes.Identifier, nodes.Scope)):
            return value
        self.report(
            f"Expression of type {type(value).__name__} cannot be a Type")

    def declare(self, name: str):
        if name in self.declared:
            self.report(f"Name {name!r} already bound in current scope.")
        self.declared.add(name)

    def parse_use(self):
        use = self.expect(Token.Type.USE)
        typ = self.type_expression()
        if isinstance(typ, nodes.Identifier) and self.match(Token.Type.ASSIGN):
            typ2 = self.type_expression()
            node = nodes.ImportAs(use, typ2, typ)
        else:
            node = nodes.Import(use, typ)
        self.expect(Token.Type.SCOLON)
        self.declare(node.bind)
        return node

    def parse_struct(self):
        klass = self.expect(Token.Type.STRUCT)
        name = self.expect(Token.Type.ID)
        self.declare(name.lexeme)
        body = self._parse_struct_body()
        return nodes.Struct(klass, name, body)

    def parse(self):
        while True:
            match self.current.typ:
                case Token.Type.IF:
                    return self.parse_if()
                case Token.Type.WHILE:
                    return self.parse_while()
                case Token.Type.RETURN:
                    return self.parse_return()
                case Token.Type.FOR:
                    return self.parse_for()
                case Token.Type.LBRACE:
                    return self.parse_block()
                case Token.Type.CONTINUE:
                    if not self.ctx.test(_S.LOOP):
                        self.report("'continue' used outside a loop")
                    self.expect(Token.Type.SCOLON)
                    return nodes.Continue(self.consume())
                case Token.Type.BREAK:
                    if not self.ctx.test(_S.LOOP):
                        self.report("'break' used outside a loop")
                    self.expect(Token.Type.SCOLON)
                    return nodes.Break(self.consume())
                case Token.Type.SCOLON:
                    self.consume()
                    continue
                case Token.Type.USE:
                    return self.parse_use()
                case Token.Type.STRUCT:
                    return self.parse_struct()
                case Token.Type.FN:
                    return self.parse_proc()
                case Token.Type.EOT:
                    break
                case _:
                    node = self.parse_assign()
                    if node is not None:
                        self.expect(Token.Type.SCOLON)
                        return node
                    self.report(f"Unexpected token {self.current}")


def Parser(lexer: ty.Iterable[Token]) -> ty.Generator[nodes.Node, None, None]:
    "LL(1) parser for Jack. EOT must be the last token in the Token Stream (lexer)"
    parser = _Parser_helper(lexer)
    while True:
        node = parser.parse()
        if node is None:
            break
        yield node
