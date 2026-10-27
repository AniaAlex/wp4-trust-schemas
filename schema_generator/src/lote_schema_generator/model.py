"""Reading the hand-maintained models: what the generators take from a model before they express it in a binding."""
import copy

# check types no schema language expresses: the validator's code runs them (core model and profile overlays)
CODE_ONLY = ("x509-certificate", "cert-same-key-subject", "cert-org-matches")


def allowed(model):
    """The model without the components its track forbids (max 0): what the schemas and profiles are generated from."""
    m = copy.deepcopy(model)
    for s in m["structures"].values():
        s["components"] = [c for c in s["components"] if c.get("max") != 0]
    return m
