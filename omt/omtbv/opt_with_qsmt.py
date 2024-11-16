"""
Reduce OMT(BV) to QSMT and call SMT solvers
that support quantified bit-vector formulas
- Z3
- CVC5
- Q3B
- ...?
"""

import z3
from omt.utils.bin_solver import solve_with_bin_smt


def opt_with_qsmt(fml: z3.ExprRef, obj: z3.ExprRef, minimize: bool, solver: str):
    """ Quantified Satisfaction based OMT
    """
    obj_misc = z3.BitVec(str(obj) + "m", obj.size())
    new_fml = z3.substitute(fml, (obj, obj_misc))
    # TODO: bvule or < (distinguish between unsigned and signed...)
    if minimize:
        qfml = z3.And(fml,
                      z3.ForAll([obj_misc], z3.Implies(new_fml, z3.ULE(obj, obj_misc))))
    else:
        qfml = z3.And(fml,
                      z3.ForAll([obj_misc], z3.Implies(new_fml, z3.ULE(obj_misc, obj))))
    return solve_with_bin_smt("BV", qfml=qfml, solver_name=solver)


def demo_qsmt():
    import time
    x, y, z = z3.BitVecs("x y z", 16)
    fml = z3.And(z3.UGT(y, 0), z3.ULT(y, 10))
    print("start solving")
    res = opt_with_qsmt(fml, y, minimize=True, solver="z3")
    print(res)
    start = time.time()
    print("solving time: ", time.time() - start)


if __name__ == '__main__':
    demo_qsmt()