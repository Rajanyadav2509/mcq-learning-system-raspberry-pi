import tkinter as tk
import database_manager

BG = "#0B1220"
PANEL = "#1A2538"
CARD = "#204B8F"
HOVER = "#2F65BF"
CORRECT_COLOR = "#28A745"
WRONG_COLOR = "#DC3545"
DIM_COLOR = "#3A4A63"

class CircularTimer(tk.Canvas):
    def __init__(self, master, seconds=15, size=100, callback=None):
        super().__init__(master, width=size, height=size, bg=BG, highlightthickness=0)
        self.seconds = seconds
        self.remaining = seconds
        self.callback = callback
        self.after_id = None

        self.create_oval(10,10,size-10,size-10, outline="#243449", width=8)
        self.arc = self.create_arc(10,10,size-10,size-10,start=90,extent=360,
                                   style="arc",outline="#00ffcc",width=8)
        self.text = self.create_text(size//2,size//2,text=str(seconds),
                                     fill="white",font=("Segoe UI",20,"bold"))

    def start(self):
        self.stop()
        self.remaining = self.seconds
        self._tick()

    def stop(self):
        if self.after_id:
            self.after_cancel(self.after_id)
            self.after_id=None

    def _tick(self):
        self.itemconfig(self.text,text=str(self.remaining))
        color="#00ffcc" if self.remaining>10 else "#ffcc00" if self.remaining>5 else "#ff4040"
        self.itemconfig(self.arc,outline=color)
        self.itemconfig(self.arc,extent=360*(self.remaining/self.seconds))
        if self.remaining<=0:
            self.after_id=None
            if self.callback:
                self.callback()
            return
        self.remaining-=1
        self.after_id=self.after(1000,self._tick)


class MCQApplication(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MCQ Based Learning Platform")
        self.geometry("1600x900")
        self.configure(bg=BG)

        self.questions = database_manager.get_all_questions()
        self.current_idx = 0
        self.answer_locked = False  # prevents double-clicks / late clicks after reveal
        self.question_anim_id = None  # tracks the typewriter animation's after() call

        self.setup_ui()
        self.load_question()

    def setup_ui(self):
        header = tk.Frame(self,bg=BG)
        header.pack(fill="x",padx=40,pady=25)

        tk.Label(header,text="MCQ BASED LEARNING PLATFORM",
                 font=("Segoe UI",28,"bold"),
                 fg="white",bg=BG).pack(side="left")

        self.counter = tk.Label(header,font=("Segoe UI",18,"bold"),
                                fg="#B8C7E0",bg=BG)
        self.counter.pack(side="right",padx=20)

        # Timer now calls self.time_up when it hits 0, instead of jumping straight
        # to the next question.
        self.timer = CircularTimer(header,callback=self.time_up)
        self.timer.pack(side="right")

        qframe = tk.Frame(self,bg=PANEL,height=230,
                          highlightbackground="#4A77C9",
                          highlightthickness=2)
        qframe.pack(fill="x",padx=40,pady=(10,25))
        qframe.pack_propagate(False)

        self.question = tk.Label(
            qframe,
            text="",
            bg=PANEL,
            fg="white",
            font=("Segoe UI",22,"bold"),
            wraplength=1450,
            justify="center"
        )
        self.question.place(relx=.5,rely=.5,anchor="center")

        self.opt_frame = tk.Frame(self,bg=BG)
        self.opt_frame.pack(fill="both",expand=True,padx=40,pady=10)

        for i in range(2):
            self.opt_frame.columnconfigure(i,weight=1,uniform="a")
            self.opt_frame.rowconfigure(i,weight=1,uniform="a")

        self.buttons=[]

        for i in range(4):
            lbl = tk.Label(
                self.opt_frame,
                bg=CARD,
                fg="white",
                font=("Segoe UI",16),
                wraplength=600,
                justify="left",
                anchor="nw",
                padx=20,
                pady=20,
                bd=0,
                cursor="hand2"
            )
            lbl.bind("<Enter>",lambda e,w=lbl:self._hover(w,True))
            lbl.bind("<Leave>",lambda e,w=lbl:self._hover(w,False))
            lbl.bind("<Button-1>",lambda e,i=i:self.check_answer(i))
            lbl.grid(row=i//2,column=i%2,
                     sticky="nsew",
                     padx=12,pady=12,
                     ipady=20)
            self.buttons.append(lbl)

    def _hover(self, widget, entering):
        # Only apply hover highlight while the question is still "live"
        if self.answer_locked:
            return
        widget.config(bg=HOVER if entering else CARD)

    def load_question(self):
        # Always match the admin panel: re-read the database before each
        # question, so a question uploaded or deleted in the panel shows
        # up (or disappears) even while the quiz is already running.
        # If the database cannot be read right now, keep the questions
        # already loaded instead of crashing.
        try:
            self.questions = database_manager.get_all_questions()
        except Exception:
            pass

        if self.current_idx>=len(self.questions):
            self.timer.stop()
            if self.question_anim_id:
                self.after_cancel(self.question_anim_id)
                self.question_anim_id = None
            self.question.config(text="Quiz Completed!")
            for b in self.buttons:
                b.config(text="",bg=CARD)
            return

        q=self.questions[self.current_idx]
        self.current_question = q
        self.answer_locked = False

        self.counter.config(
            text=f"Question {self.current_idx+1}/{len(self.questions)}"
        )

        for i,opt in enumerate(q["options"]):
            self.buttons[i].config(text=f"{chr(65+i)}. {opt}",bg=CARD)

        self.animate_question(q["question"])

    def animate_question(self, full_text, i=0, speed=20):
        """Typewriter effect: reveals the question text one character at a time."""
        if self.question_anim_id:
            self.after_cancel(self.question_anim_id)
            self.question_anim_id = None

        self.question.config(text=full_text[:i])

        if i < len(full_text):
            self.question_anim_id = self.after(
                speed, lambda: self.animate_question(full_text, i + 1, speed)
            )
        else:
            self.question_anim_id = None
            # Only start the countdown once the question has fully typed out
            self.timer.start()

    def _correct_index(self, q):
        """
        Figures out which option index is correct, regardless of how
        database_manager stores it (index, letter, or the answer text).
        """
        answer = q.get("answer", q.get("correct_answer", q.get("correct")))
        options = q["options"]

        if isinstance(answer, int):
            return answer
        if isinstance(answer, str):
            a = answer.strip()
            # letter form: "A" / "b" / "C."
            if len(a) == 1 and a.upper() in "ABCD":
                return "ABCD".index(a.upper())
            # matches option text directly
            for i, opt in enumerate(options):
                if str(opt).strip().lower() == a.lower():
                    return i
        return None

    def check_answer(self, idx):
        if self.answer_locked:
            return
        self.timer.stop()
        self.reveal_answer(selected_idx=idx)

    def time_up(self):
        if self.answer_locked:
            return
        self.reveal_answer(selected_idx=None)

    def reveal_answer(self, selected_idx):
        self.answer_locked = True
        correct_idx = self._correct_index(self.current_question)

        for i, btn in enumerate(self.buttons):
            if correct_idx is not None and i == correct_idx:
                btn.config(bg=CORRECT_COLOR)
            elif selected_idx is not None and i == selected_idx:
                btn.config(bg=WRONG_COLOR)
            else:
                btn.config(bg=DIM_COLOR)

        # pause on the reveal for 1.5s, then move on
        self.after(1500, self.next_question)

    def next_question(self):
        self.current_idx+=1
        self.load_question()


if __name__=="__main__":
    MCQApplication().mainloop()