# coding: utf-8
"""
Augmenting Z3 using PySMT, e.g., interpolant generation
"""
import logging
import z3
from pysmt.logics import QF_BV  # AUTO
from pysmt.oracles import get_logic
from pysmt.shortcuts import Bool, get_model, Not, Solver
from pysmt.shortcuts import EqualsOrIff
from pysmt.shortcuts import Portfolio
from pysmt.shortcuts import Symbol, And
from pysmt.shortcuts import binary_interpolant, sequence_interpolant
from pysmt.typing import INT, REAL, BVType
# BV1, BV8, BV16, BV32, BV64, BV128


logger = logging.getLogger(__name__)


# NOTE: both pysmt and z3 have a class "Solver"


def to_pysmt_vars(z3vars: [z3.ExprRef]):
    res = []
    for v in z3vars:
        if z3.is_int(v):
            res.append(Symbol(v.decl().name(), INT))
        elif z3.is_real(v):
            res.append(Symbol(v.decl().name(), REAL))
        elif z3.is_bv(v):
            res.append(Symbol(v.decl().name(), BVType(v.sort().size())))
        else:
            raise NotImplementedError
    return res
    # return [Symbol(v.decl().name(),
    #              INT if v.is_int() else REAL) for v in z3vars]


class PySMTSolver(z3.Solver):

    def __init__(self, debug=False):
        super(PySMTSolver, self).__init__()

    @staticmethod
    def convert(zf: z3.ExprRef):
        """
        FIXME: if we do not call "pysmt_vars = ...", z3 will report naming warning..
        """
        zvs = z3.z3util.get_vars(zf)
        # pysmt_vars = [Symbol(v.decl().name(), INT if v.is_int() else REAL) for v in zvs]
        pysmt_vars = to_pysmt_vars(zvs)
        z3s = Solver(name='z3')
        pysmt_fml = z3s.converter.back(zf)
        return pysmt_vars, pysmt_fml

    def check_with_pysmt(self):
        """TODO: build a Z3 model?"""
        z3fml = z3.And(self.assertions())
        pysmt_vars, pysmt_fml = PySMTSolver.convert(z3fml)
        # print(pysmt_vars)
        f_logic = get_logic(pysmt_fml)
        try:
            with Solver(logic=f_logic) as solver:
                solver.add_assertion(pysmt_fml)
                res = solver.solve()
                if res:
                    # print(solver.get_model())
                    return z3.sat
                return z3.unsat
        except Exception:
            return z3.unknown

    def all_smt(self, keys: [z3.ExprRef], bound=5):
        """Sample k models"""
        z3fml = z3.And(self.assertions())
        _, pysmt_fml = PySMTSolver.convert(z3fml)
        target_logic = get_logic(pysmt_fml)

        pysmt_var_keys = to_pysmt_vars(keys)
        # print("Target Logic: %s" % target_logic)

        with Solver(logic=target_logic) as solver:
            solver.add_assertion(pysmt_fml)
            iteration = 0
            while solver.solve():
                partial_model = [EqualsOrIff(k, solver.get_value(k)) for k in pysmt_var_keys]
                print(partial_model)
                solver.add_assertion(Not(And(partial_model)))
                iteration += 1
                if iteration >= bound: break

    def efsmt(self, evars: [z3.ExprRef], uvars: [z3.ExprRef], z3fml: z3.ExprRef, logic=QF_BV, maxloops=None,
              esolver_name="z3", fsolver_name="z3",
              verbose=False):
        """Solves exists x. forall y. phi(x, y)"""

        _, phi = PySMTSolver.convert(z3fml)
        y = to_pysmt_vars(uvars)  # universally quantified
        y = set(y)
        x = phi.get_free_variables() - y

        with Solver(logic=logic, name=esolver_name) as esolver:
            esolver.add_assertion(Bool(True))
            loops = 0
            result = "unknown"
            while maxloops is None or loops <= maxloops:
            # while True:
                loops += 1
                eres = esolver.solve()
                if not eres:
                    result = "unsat"
                    break
                else:
                    tau = {v: esolver.get_value(v) for v in x}
                    sub_phi = phi.substitute(tau).simplify()
                    if verbose: print("%d: Tau = %s" % (loops, tau))

                    fmodel = get_model(Not(sub_phi),
                                       logic=logic, solver_name=fsolver_name)
                    if fmodel is None:
                        result = "sat"
                        break
                    else:
                        sigma = {v: fmodel[v] for v in y}
                        sub_phi = phi.substitute(sigma).simplify()
                        if verbose: print("%d: Sigma = %s" % (loops, sigma))
                        esolver.add_assertion(sub_phi)
            return result

def test():
    x, y, z = z3.Ints("x y z")
    fml = z3.And(x > 10, y < 19, z == 3.0)
    sol = PySMTSolver()
    sol.add(fml)
    print(sol.check())
    # sol.all_smt([x, y])

    fml_a = z3.And(x <= 1, y < x)
    fml_b = z3.And(y >= z, z > 0)
    print(sol.binary_interpolant(fml_a, fml_b))
    print(sol.sequence_interpolant([fml_a, fml_b]))

# test()
