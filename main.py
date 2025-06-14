import tkinter as tk
from tkinter import simpledialog, messagebox
from pysat.solvers import Glucose3
from itertools import combinations

CELL_SIZE = 40

# 任意にサイズ変更可
ROWS = 3
COLS = 3

VALID_KEYS = {"w", "b", "s", "1", "2", "3", "4"}

class AkariApp:
    def __init__(self, master):
        self.master = master
        self.board = [["." for _ in range(COLS)] for _ in range(ROWS)]
        self.cells = [[None for _ in range(COLS)] for _ in range(ROWS)]
        self.selected_cell = None
        self.canvas = tk.Canvas(master, width=COLS*CELL_SIZE, height=ROWS*CELL_SIZE)
        self.canvas.pack()
        self.draw_grid()
        self.canvas.bind("<Button-1>", self.on_click)
        master.bind("<Key>", self.on_keypress)

        self.solve_button = tk.Button(master, text="Solve", command=self.solve)
        self.solve_button.pack(side=tk.LEFT)

        self.next_button = tk.Button(master, text="Next", command=self.show_next_solution)
        self.next_button.pack(side=tk.LEFT)

        self.solutions = []
        self.current_index = 0
        self.var_map = {}

    def draw_grid(self):
        for r in range(ROWS):
            for c in range(COLS):
                x1, y1 = c * CELL_SIZE, r * CELL_SIZE
                x2, y2 = x1 + CELL_SIZE, y1 + CELL_SIZE
                rect = self.canvas.create_rectangle(x1, y1, x2, y2, fill="white", outline="gray")
                text = self.canvas.create_text((x1+x2)//2, (y1+y2)//2, text="", font=("Arial", 16))
                self.cells[r][c] = (rect, text)

    def update_display(self):
        for r in range(ROWS):
            for c in range(COLS):
                val = self.board[r][c]
                rect, text = self.cells[r][c]
                if val == "B":
                    self.canvas.itemconfig(rect, fill="black")
                    self.canvas.itemconfig(text, text="", fill="white")
                elif val in "01234":
                    self.canvas.itemconfig(rect, fill="white")
                    self.canvas.itemconfig(text, text=val, fill="black")
                else:
                    self.canvas.itemconfig(rect, fill="white")
                    self.canvas.itemconfig(text, text="", fill="black")

    def on_click(self, event):
        c, r = event.x // CELL_SIZE, event.y // CELL_SIZE
        if 0 <= r < ROWS and 0 <= c < COLS:
            self.selected_cell = (r, c)
            self.highlight_selected()

    def on_keypress(self, event):
        key = event.char.lower()
        if self.selected_cell and key in VALID_KEYS:
            r, c = self.selected_cell
            self.board[r][c] = key.upper() if key == 'b' else key
            self.update_display()
            self.highlight_selected()

    def highlight_selected(self):
        for r in range(ROWS):
            for c in range(COLS):
                rect, _ = self.cells[r][c]
                if self.selected_cell == (r, c):
                    self.canvas.itemconfig(rect, outline="blue", width=3)
                else:
                    self.canvas.itemconfig(rect, outline="gray", width=1)

    def solve(self):
        self.solutions = self.enumerate_solutions()
        self.current_index = 0
        if self.solutions:
            messagebox.showinfo("Solved", f"{len(self.solutions)} 解が見つかりました。Next で表示できます。")
            self.show_next_solution()
        else:
            messagebox.showerror("No Solution", "解が見つかりませんでした。")

    def show_next_solution(self):
        if not self.solutions:
            return
        model = self.solutions[self.current_index]
        vars_true = set(v for v in model if v > 0)
        for r in range(ROWS):
            for c in range(COLS):
                rect, text = self.cells[r][c]
                if self.board[r][c] == ".":
                    var = self.var_map.get((r, c))
                    if var in vars_true:
                        self.canvas.itemconfig(text, text="*", fill="red")
                    else:
                        self.canvas.itemconfig(text, text="", fill="black")
        self.current_index = (self.current_index + 1) % len(self.solutions)

    def enumerate_solutions(self):
        board = self.board
        H, W = ROWS, COLS
        self.var_map = {}
        var_id = 1
        for r in range(H):
            for c in range(W):
                if board[r][c] == ".":
                    self.var_map[(r, c)] = var_id
                    var_id += 1

        def in_bounds(r, c):
            return 0 <= r < H and 0 <= c < W

        def line_of_sight(r, c):
            for dr, dc in [(-1,0), (1,0), (0,-1), (0,1)]:
                nr, nc = r + dr, c + dc
                while in_bounds(nr, nc) and board[nr][nc] not in "01234B":
                    if (nr, nc) in self.var_map:
                        yield (nr, nc)
                    nr += dr
                    nc += dc

        def illuminated_vars(r, c):
            vars = []
            if (r, c) in self.var_map:
                vars.append(self.var_map[(r, c)])
            for (nr, nc) in line_of_sight(r, c):
                if (nr, nc) != (r, c):
                    vars.append(self.var_map[(nr, nc)])
            return vars

        cnf = []

        for (r, c), v1 in self.var_map.items():
            for (nr, nc) in line_of_sight(r, c):
                v2 = self.var_map[(nr, nc)]
                if v1 < v2:
                    cnf.append([-v1, -v2])

        for r in range(H):
            for c in range(W):
                if board[r][c] == ".":
                    clause = illuminated_vars(r, c)
                    cnf.append(clause)

        for r in range(H):
            for c in range(W):
                if board[r][c] in "01234":
                    N = int(board[r][c])
                    neighbors = []
                    for dr, dc in [(-1,0), (1,0), (0,-1), (0,1)]:
                        nr, nc = r + dr, c + dc
                        if in_bounds(nr, nc) and (nr, nc) in self.var_map:
                            neighbors.append(self.var_map[(nr, nc)])
                    for combo in combinations(neighbors, N+1):
                        assert(len(combo) == N+1)
                        cnf.append([-v for v in combo])
                    for combo in combinations(neighbors, len(neighbors) - N + 1):
                        assert(len(combo) == len(neighbors) - N + 1)
                        cnf.append([v for v in combo])

        solver = Glucose3()
        solver.append_formula(cnf)

        all_models = []
        while solver.solve():
            model = solver.get_model()
            all_models.append(model)
            blocking_clause = [-v for v in model if v > 0 and v in self.var_map.values()]
            solver.add_clause(blocking_clause)

        return all_models


# ==== 実行 ====
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Akari GUI + All Solutions + Keyboard + Resize")
    app = AkariApp(root)
    root.mainloop()
