import dataclasses as dt
import typing

from .token import Token

type Scope = dict[str, Node]


class Node:
    def visit[T](self, visitor: "BaseVisitor[T]") -> T:
        target = self.__class__.__name__
        selected = f"visit_{target.lower()}"
        return getattr(visitor, selected)(self)


class Expr(Node): ...


@dt.dataclass(slots=True)
class TypeExpr(Expr):
    token: Token


@dt.dataclass(slots=True)
class Break(Node):
    keyword: Token


@dt.dataclass(slots=True)
class Continue(Node):
    keyword: Token


@dt.dataclass(slots=True)
class Return(Node):
    ret: Token
    expr: Expr | None


@dt.dataclass(slots=True)
class Decl(Node):
    name: Token
    type: TypeExpr


@dt.dataclass(slots=True)
class FDecl(Decl):
    free: Token


@dt.dataclass(slots=True)
class FDeclInit(FDecl):
    init: Expr


@dt.dataclass(slots=True)
class MethodDecl(Node):
    fn: Token
    name: Token
    params: list[Decl]
    return_type: TypeExpr
    scope: Scope = dt.field(default_factory=dict, init=False)


@dt.dataclass(slots=True)
class FunctionDecl(MethodDecl):
    free: Token


@dt.dataclass(slots=True)
class Block(Node):
    brace: Token
    members: list[Node]
    scope: Scope = dt.field(default_factory=dict, init=False)


@dt.dataclass(slots=True)
class Method(MethodDecl):
    body: Block


@dt.dataclass(slots=True)
class Function(FunctionDecl):
    body: Block


@dt.dataclass(slots=True)
class Import(Node):
    using: Token
    path: list[Token]
    upcnt: int


@dt.dataclass(slots=True)
class TypeAlias(Node):
    using: Token
    name: Token
    typ: TypeExpr


@dt.dataclass(slots=True)
class Class(Node):
    type Members = list[Decl | MethodDecl | Import | TypeAlias]
    class_: Token
    name: Token
    members: Members
    scope: Scope = dt.field(default_factory=dict, init=False)


@dt.dataclass(slots=True)
class Generic(Class):
    params: list[Token]


@dt.dataclass(slots=True)
class If(Node):
    if_: Token
    cond: Expr
    body: Block
    else_: tuple[Token, Block] | None


@dt.dataclass(slots=True)
class While(Node):
    while_: Token
    cond: Expr
    body: Block


@dt.dataclass(slots=True)
class Assign(Node):
    left: Expr
    op: Token
    right: Expr


@dt.dataclass(slots=True)
class Init(Assign):
    typ: TypeExpr


@dt.dataclass(slots=True)
class For(Node):
    for_: Token
    bind: Token
    expr: Expr
    body: Block


# fmt: off
@dt.dataclass(slots=True)
class TypeCall(TypeExpr):
    generic: TypeExpr
    params: list[TypeExpr]

@dt.dataclass(slots=True)
class TypeMember(TypeExpr):
    left: TypeExpr
    right: Token

class TypeName(TypeExpr): ...
class TypeAuto(TypeExpr): ...

@dt.dataclass(slots=True)
class TypeDeduce(TypeAuto):
    operand: Expr

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
class Is(_BinExpr): ...
class IsNot(_BinExpr): ...


class BaseVisitor[T](typing.Protocol): ...

class TypeExprVisitor[T](BaseVisitor[T], typing.Protocol):
    def visit_typename(self, expr: TypeName) -> T: ...
    def visit_typeauto(self, expr: TypeAuto) -> T: ...
    def visit_typemember(self, expr: TypeMember) -> T: ...
    def visit_typecall(self, expr: TypeCall) -> T: ...
    def visit_typededuce(self, expr: TypeDeduce) -> T: ...


class ExprVisitor[T](BaseVisitor[T], typing.Protocol):
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
    def visit_is(self, expr: Is) -> T: ...
    def visit_isnot(self, expr: IsNot) -> T: ...


class StmtVisitor[T](BaseVisitor[T], typing.Protocol):
    def visit_class(self, stmt: Class) -> T: ...
    def visit_block(self, stmt: Block) -> T: ...
    def visit_generic(self, stmt: Generic) -> T: ...
    def visit_methoddecl(self, stmt: MethodDecl) -> T: ...
    def visit_if(self, stmt: If) -> T: ...
    def visit_return(self, stmt: Return) -> T: ...
    def visit_import(self, stmt: Import) -> T: ...
    def visit_while(self, stmt: While) -> T: ...
    def visit_for(self, stmt: For) -> T: ...
    def visit_method(self, stmt: Method) -> T: ...
    def visit_functiondecl(self, stmt: FunctionDecl) -> T: ...
    def visit_function(self, stmt: Function) -> T: ...
    def visit_fdecl(self, stmt: FDecl) -> T: ...
    def visit_decl(self, stmt: Decl) -> T: ...
    def visit_assign(self, stmt: Assign) -> T: ...
    def visit_continue(self, stmt: Continue) -> T: ...
    def visit_break(self, stmt: Break) -> T: ...
    def visit_fdeclinit(self, stmt: FDeclInit) -> T: ...
    def visit_init(self, stmt: Init) -> T: ...


class Visitor[T](
    TypeExprVisitor[T],
    ExprVisitor[T],
    StmtVisitor[T],
    typing.Protocol
):...
# fmt: on
