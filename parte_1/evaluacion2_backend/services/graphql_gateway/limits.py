from graphql import GraphQLError, ValidationRule
from graphql.language import FieldNode, FragmentSpreadNode, InlineFragmentNode, IntValueNode, VariableNode

MAX_PAGE = 50
LIST_FIELDS = {"nodes", "items", "topProducts"}
PAGED_FIELDS = {"products", "myOrders"}
DEFAULT_LIST_WEIGHT = 10


def cost_limit(max_cost):
    class CostLimit(ValidationRule):
        def enter_operation_definition(self, node, *args):
            total = self.cost(node.selection_set, 1, set())
            if total > max_cost:
                self.report_error(GraphQLError(f"Consulta demasiado costosa: {total} excede el maximo {max_cost}", node))

        def page_size(self, field):
            for argument in field.arguments or []:
                if argument.name.value == "first":
                    if isinstance(argument.value, IntValueNode):
                        return min(int(argument.value.value), MAX_PAGE)
                    if isinstance(argument.value, VariableNode):
                        return MAX_PAGE
            return 20

        def cost(self, selection_set, multiplier, seen):
            if selection_set is None:
                return 0
            total = 0
            for selection in selection_set.selections:
                if isinstance(selection, FieldNode):
                    name = selection.name.value
                    if name.startswith("__"):
                        continue
                    total += multiplier
                    inner = multiplier
                    if name in PAGED_FIELDS:
                        inner = multiplier * self.page_size(selection)
                    elif name in LIST_FIELDS:
                        inner = multiplier * (DEFAULT_LIST_WEIGHT if name != "nodes" else 1)
                    total += self.cost(selection.selection_set, inner, seen)
                elif isinstance(selection, InlineFragmentNode):
                    total += self.cost(selection.selection_set, multiplier, seen)
                elif isinstance(selection, FragmentSpreadNode):
                    fragment_name = selection.name.value
                    if fragment_name in seen:
                        continue
                    fragment = self.context.get_fragment(fragment_name)
                    if fragment:
                        total += self.cost(fragment.selection_set, multiplier, seen | {fragment_name})
            return total

    return CostLimit
