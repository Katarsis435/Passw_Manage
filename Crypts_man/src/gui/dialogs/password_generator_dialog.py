# src/gui/widgets/password_generator_dialog.py
import tkinter as tk
from tkinter import ttk


class PasswordGeneratorDialog:
    """Password generator dialog with configuration options"""

    def __init__(self, parent, generator, callback):
        self.parent = parent
        self.generator = generator
        self.callback = callback
        self.result = None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Generate Password")
        self.dialog.geometry("500x600")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._create_widgets()
        self._center_dialog()

    def _center_dialog(self):
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (600 // 2)
        self.dialog.geometry(f"+{x}+{y}")

    def _create_widgets(self):
        # Main frame with scrolling
        canvas = tk.Canvas(self.dialog)
        scrollbar = ttk.Scrollbar(self.dialog, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        main_frame = ttk.Frame(scrollable_frame, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Length setting
        length_frame = ttk.LabelFrame(main_frame, text="Password Length", padding="10")
        length_frame.pack(fill=tk.X, pady=5)

        self.length_var = tk.IntVar(value=16)
        length_scale = ttk.Scale(length_frame, from_=8, to=64, variable=self.length_var,
                                 orient=tk.HORIZONTAL, command=self._update_length_label)
        length_scale.pack(fill=tk.X)

        self.length_label = ttk.Label(length_frame, text="Length: 16")
        self.length_label.pack()

        # Character sets
        chars_frame = ttk.LabelFrame(main_frame, text="Character Sets", padding="10")
        chars_frame.pack(fill=tk.X, pady=5)

        self.use_upper = tk.BooleanVar(value=True)
        self.use_lower = tk.BooleanVar(value=True)
        self.use_digits = tk.BooleanVar(value=True)
        self.use_symbols = tk.BooleanVar(value=True)

        ttk.Checkbutton(chars_frame, text="Uppercase (A-Z)", variable=self.use_upper,
                        command=self._generate).pack(anchor=tk.W)
        ttk.Checkbutton(chars_frame, text="Lowercase (a-z)", variable=self.use_lower,
                        command=self._generate).pack(anchor=tk.W)
        ttk.Checkbutton(chars_frame, text="Digits (0-9)", variable=self.use_digits,
                        command=self._generate).pack(anchor=tk.W)
        ttk.Checkbutton(chars_frame, text="Symbols (!@#$%^&*)", variable=self.use_symbols,
                        command=self._generate).pack(anchor=tk.W)

        # Options
        options_frame = ttk.LabelFrame(main_frame, text="Options", padding="10")
        options_frame.pack(fill=tk.X, pady=5)

        self.exclude_ambiguous = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Exclude ambiguous characters (l, I, 1, 0, O)",
                        variable=self.exclude_ambiguous, command=self._generate).pack(anchor=tk.W)

        # Memorable passphrase option
        self.use_memorable = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Generate memorable passphrase",
                        variable=self.use_memorable, command=self._toggle_memorable).pack(anchor=tk.W)

        # Words count for memorable
        self.words_frame = ttk.Frame(options_frame)
        self.words_frame.pack(fill=tk.X, pady=5)
        ttk.Label(self.words_frame, text="Number of words:").pack(side=tk.LEFT)
        self.words_var = tk.IntVar(value=4)
        ttk.Spinbox(self.words_frame, from_=3, to=6, textvariable=self.words_var,
                    width=5, command=self._generate).pack(side=tk.LEFT, padx=5)
        self.words_frame.pack_forget()

        # Generated password display
        display_frame = ttk.LabelFrame(main_frame, text="Generated Password", padding="10")
        display_frame.pack(fill=tk.X, pady=5)

        self.password_var = tk.StringVar()
        self.password_entry = ttk.Entry(display_frame, textvariable=self.password_var,
                                        font=('Courier', 11), state='readonly')
        self.password_entry.pack(fill=tk.X, pady=5)

        # Copy button
        ttk.Button(display_frame, text="Copy to Clipboard", command=self._copy_to_clipboard).pack()

        # Strength meter
        strength_frame = ttk.LabelFrame(main_frame, text="Password Strength", padding="10")
        strength_frame.pack(fill=tk.X, pady=5)

        self.strength_meter = ttk.Progressbar(strength_frame, length=300, mode='determinate')
        self.strength_meter.pack(pady=5)

        self.strength_label = ttk.Label(strength_frame, text="")
        self.strength_label.pack()

        self.feedback_text = tk.Text(strength_frame, height=4, width=50, wrap=tk.WORD)
        self.feedback_text.pack(pady=5)

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)

        ttk.Button(button_frame, text="Generate New", command=self._generate).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Use This Password", command=self._use_password).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.dialog.destroy).pack(side=tk.RIGHT, padx=5)

        # Generate initial password
        self._generate()

        # Pack scrollable area
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _update_length_label(self, *args):
        self.length_label.config(text=f"Length: {int(self.length_var.get())}")
        self._generate()

    def _toggle_memorable(self):
        if self.use_memorable.get():
            self.words_frame.pack(fill=tk.X, pady=5)
        else:
            self.words_frame.pack_forget()
        self._generate()

    def _generate(self):
        """Generate new password"""
        try:
            if self.use_memorable.get():
                password = self.generator.generate_memorable(words=self.words_var.get())
            else:
                password = self.generator.generate(
                    length=int(self.length_var.get()),
                    use_upper=self.use_upper.get(),
                    use_lower=self.use_lower.get(),
                    use_digits=self.use_digits.get(),
                    use_symbols=self.use_symbols.get(),
                    exclude_ambiguous=self.exclude_ambiguous.get()
                )

            self.password_var.set(password)
            self._update_strength(password)
        except Exception as e:
            self.password_var.set(f"Error: {e}")

    def _update_strength(self, password):
        """Update strength meter and feedback"""
        strength = self.generator.estimate_strength(password)

        # Update progress bar
        self.strength_meter['value'] = (strength['score'] + 1) * 20
        self.strength_label.config(text=f"Strength: {strength['rating']}")

        # Update colors based on strength
        colors = ['#ff4444', '#ff8844', '#ffcc00', '#88cc44', '#44cc44']
        self.strength_meter['style'] = f"green.Horizontal.TProgressbar"

        # Update feedback
        self.feedback_text.delete(1.0, tk.END)
        if strength.get('feedback'):
            for msg in strength['feedback']:
                self.feedback_text.insert(tk.END, f"• {msg}\n")

        if strength.get('crack_time'):
            self.feedback_text.insert(tk.END, f"\nEstimated crack time: {strength['crack_time']}")

    def _copy_to_clipboard(self):
        """Copy generated password to clipboard"""
        password = self.password_var.get()
        if password and not password.startswith("Error"):
            self.parent.clipboard_clear()
            self.parent.clipboard_append(password)

    def _use_password(self):
        """Use generated password"""
        self.result = self.password_var.get()
        if self.callback and not self.result.startswith("Error"):
            self.callback(self.result)
        self.dialog.destroy()
