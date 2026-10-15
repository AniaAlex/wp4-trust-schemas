"""Reading the hand-maintained models: what the generators take from a model before they express it in a binding."""
import copy


def allowed(model):
    """The model without the components its track forbids (max 0): what the schemas and profiles are generated from."""
    m = copy.deepcopy(model)
    for s in m["structures"].values():
        s["components"] = [c for c in s["components"] if c.get("max") != 0]
    return m
