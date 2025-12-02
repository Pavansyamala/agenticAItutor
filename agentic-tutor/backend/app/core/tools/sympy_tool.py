# backend/app/core/tools/sympy_verifier.py
from sympy import sympify, simplify, Eq, solve, Matrix, symbols
from sympy.parsing.latex import parse_latex
import logging

logger = logging.getLogger(__name__)

class SymPyVerifier:
    @staticmethod
    def verify_equality(student_expr: str, expected_expr: str) -> dict:
        """Verify if two symbolic expressions are mathematically equal"""
        try:
            # Try LaTeX first (common in Linear Algebra)
            try:
                s = parse_latex(student_expr)
                e = parse_latex(expected_expr)
            except:
                s = sympify(student_expr, locals={"I": 1j})
                e = sympify(expected_expr, locals={"I": 1j})

            if simplify(s - e) == 0:
                return {"correct": True, "feedback": "Perfect! Your expression is mathematically equivalent."}
            else:
                return {"correct": False, "feedback": f"Not equivalent. Expected form: {expected_expr}"}
        except Exception as e:
            logger.warning(f"SymPy parsing failed: {e}")
            return {"correct": False, "feedback": "Could not parse your symbolic answer. Check syntax and LaTeX format."}

    @staticmethod
    def verify_matrix(student_str: str, expected_str: str) -> dict:
        """Verify matrix equality"""
        try:
            s_matrix = Matrix(sympify(student_str.replace("\n", ",")))
            e_matrix = Matrix(sympify(expected_str.replace("\n", ",")))
            if s_matrix.equals(e_matrix):
                return {"correct": True, "feedback": "Matrix is correct!"}
            else:
                return {"correct": False, "feedback": f"Incorrect matrix. Expected:\n{expected_str}"}
        except:
            return {"correct": False, "feedback": "Invalid matrix format."}

    @staticmethod
    def verify_solution(student_answer: str, equation: str, variable: str = "x") -> dict:
        """Verify if student solved equation correctly"""
        try:
            x = symbols(variable)
            eq = sympify(equation)
            student_sol = sympify(student_answer)
            if eq.subs(x, student_sol) == 0:
                return {"correct": True, "feedback": "Solution is correct!"}
            else:
                correct = solve(eq, x)
                return {"correct": False, "feedback": f"Incorrect. Correct solution: {correct}"}
        except:
            return {"correct": False, "feedback": "Could not verify solution."}