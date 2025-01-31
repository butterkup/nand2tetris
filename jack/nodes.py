import dataclasses as dt
import typing

from .token import Token


class Node:
    def visit[T](self, visitor: "StmtVisitor[T]") -> T:
        target = self.__class__.__name__
        selected = f"visit_{target.lower()}"
        return getattr(visitor, selected)(self)


class Expr(Node):
    ...


class Stmt(Node):
    ...


@dt.dataclass(slots=True)
class Expression(Stmt):
    expr: Expr


@dt.dataclass(slots=True)
class Break(Stmt):
    keyword: Token


@dt.dataclass(slots=True)
class Continue(Stmt):
    keyword: Token


@dt.dataclass(slots=True)
class Return(Stmt):
    ret: Token
    expr: Expr | None = None


@dt.dataclass(slots=True)
class Decl(Node):
    name: Token
    type: Expr


@dt.dataclass(slots=True)
class Block(Stmt):
    brace: Token
    members: list[Node]


@dt.dataclass(slots=True)
class FunctionDecl(Stmt):
    fn: Token
    name: Token
    params: list[Decl]
    return_type: Expr


@dt.dataclass(slots=True)
class Function(FunctionDecl):
    body: Block


@dt.dataclass(slots=True)
class Import(Stmt):
    use: Token
    path: "Scope | Identifier"

    @property
    def name(self) -> str:
        return self.path.name

    bind = name


@dt.dataclass(slots=True)
class ImportAs(Import):
    alias: "Identifier"

    @property
    def bind(self) -> str:
        return self.alias.name


@dt.dataclass(slots=True)
class Struct(Stmt):
    klass: Token
    name: Token
    members: list[Decl]


@dt.dataclass(slots=True)
class If(Stmt):
    if_: Token
    cond: Expr
    body: Block
    els: Block | None = None


@dt.dataclass(slots=True)
class While(Stmt):
    while_: Token
    cond: Expr
    body: Block


@dt.dataclass(slots=True)
class Assign(Stmt):
    left: Expr
    op: Token
    right: Expr


@dt.dataclass(slots=True)
class Init(Assign):
    value: Expr


@dt.dataclass(slots=True)
class For(Stmt):
    for_: Token
    bind: Token
    expr: Expr
    body: Block


# fmt: off
@dt.dataclass(slots=True)
class _UnExpr(Expr):
    op: Token
    operand: Expr

@dt.dataclass(slots=True)
class _BinExpr[RightT=Expr](Expr):
    left: Expr
    op: Token
    right: RightT

@dt.dataclass(slots=True)
class Primary(Expr):
    value: Token

@dt.dataclass(slots=True)
class Identifier(Primary):
    @property
    def name(self) -> str:
        return self.value.lexeme

@dt.dataclass(slots=True)
class Scope(Expr):
    op: Token
    path: list[str]

    @property
    def name(self) -> str:
        return self.path[-1]

class Subscript(_BinExpr[list[Expr]]): ...
class Call(_BinExpr[list[Expr]]): ...
class Dot(_BinExpr[Token]): ...
class Group(_UnExpr): ...
class Negate(_UnExpr): ...
class Posify(_UnExpr): ...
class Not(_UnExpr): ...
class BitNot(_UnExpr): ...
class Add(_BinExpr): ...
class Subtract(_BinExpr): ...
class Multiply(_BinExpr): ...
class Divide(_BinExpr): ...
class And(_BinExpr): ...
class Or(_BinExpr): ...
class BitAnd(_BinExpr): ...
class BitOr(_BinExpr): ...
class Equal(_BinExpr): ...
class NEqual(_BinExpr): ...
class LessT(_BinExpr): ...
class LessE(_BinExpr): ...
class GreatT(_BinExpr): ...
class GreatE(_BinExpr): ...



class ExprVisitor[T](typing.Protocol):
    def visit_primary(self, expr: Primary) -> T: ...
    def visit_subscript(self, expr: Subscript) -> T: ...
    def visit_call(self, expr: Call) -> T: ...
    def visit_dot(self, expr: Dot) -> T: ...
    def visit_group(self, expr: Group) -> T: ...
    def visit_negate(self, expr: Negate) -> T: ...
    def visit_posify(self, expr: Posify) -> T: ...
    def visit_not(self, expr: Not) -> T: ...
    def visit_bitnot(self, expr: BitNot) -> T: ...
    def visit_add(self, expr: Add) -> T: ...
    def visit_subtract(self, expr: Subtract) -> T: ...
    def visit_multiply(self, expr: Multiply) -> T: ...
    def visit_divide(self, expr: Divide) -> T: ...
    def visit_and(self, expr: And) -> T: ...
    def visit_or(self, expr: Or) -> T: ...
    def visit_bitand(self, expr: BitAnd) -> T: ...
    def visit_bitor(self, expr: BitOr) -> T: ...
    def visit_equal(self, expr: Equal) -> T: ...
    def visit_nequal(self, expr: NEqual) -> T: ...
    def visit_greatt(self, expr: GreatT) -> T: ...
    def visit_greate(self, expr: GreatE) -> T: ...
    def visit_lesst(self, expr: LessT) -> T: ...
    def visit_lesse(self, expr: LessE) -> T: ...
    def visit_scope(self, expr: Scope) -> T: ...
    def visit_identifier(self, expr: Identifier) -> T:
        return self.visit_primary(expr)


class StmtVisitor[T](ExprVisitor[T], typing.Protocol):
    def visit_struct(self, stmt: Struct) -> T: ...
    def visit_block(self, stmt: Block) -> T: ...
    def visit_functiondecl(self, stmt: FunctionDecl) -> T: ...
    def visit_if(self, stmt: If) -> T: ...
    def visit_return(self, stmt: Return) -> T: ...
    def visit_import(self, stmt: Import) -> T: ...
    def visit_importas(self, stmt: ImportAs) -> T: ...
    def visit_while(self, stmt: While) -> T: ...
    def visit_for(self, stmt: For) -> T: ...
    def visit_function(self, stmt: Function) -> T: ...
    def visit_assign(self, stmt: Assign) -> T: ...
    def visit_init(self, stmt: Init) -> T: ...
    def visit_continue(self, stmt: Continue) -> T: ...
    def visit_break(self, stmt: Break) -> T: ...
    def visit_expression(self, stmt: Expression) -> T: ...

# fmt: on
