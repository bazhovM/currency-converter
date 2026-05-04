import json
import os
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
import tkinter as tk
from tkinter import ttk, messagebox


APP_TITLE = "Currency Converter"
DATA_DIR = Path("data")
HISTORY_FILE = DATA_DIR / "history.json"
SETTINGS_FILE = DATA_DIR / "settings.json"
API_URL = "https://v6.exchangerate-api.com/v6/{api_key}/pair/{from_currency}/{to_currency}/{amount}"

COMMON_CURRENCIES = [
    "USD", "EUR", "GBP", "RUB", "CNY", "JPY", "TRY", "AED", "KZT", "UZS", "BYN", "CHF", "CAD", "AUD",
]


class CurrencyConverterApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("900x620")
        self.root.minsize(860, 580)

        DATA_DIR.mkdir(exist_ok=True)

        self.api_key_var = tk.StringVar(value=self._load_saved_api_key())
        self.from_currency_var = tk.StringVar(value="USD")
        self.to_currency_var = tk.StringVar(value="RUB")
        self.amount_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Введите данные и нажмите «Конвертировать».")

        self._build_ui()
        self._load_history_into_table()

    def _build_ui(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TFrame", background="#f4f7fb")
        style.configure("TLabel", background="#f4f7fb", font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 18, "bold"))
        style.configure("TButton", font=("Segoe UI", 10))
        style.configure("Treeview", rowheight=28, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

        container = ttk.Frame(self.root, padding=16)
        container.pack(fill="both", expand=True)

        header = ttk.Frame(container)
        header.pack(fill="x", pady=(0, 12))
        ttk.Label(header, text=APP_TITLE, style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Конвертация валют через ExchangeRate API с сохранением истории в JSON.",
        ).pack(anchor="w", pady=(4, 0))

        form = ttk.LabelFrame(container, text="Конвертация", padding=14)
        form.pack(fill="x", pady=(0, 12))
        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)

        ttk.Label(form, text="API-ключ").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=6)
        api_entry = ttk.Entry(form, textvariable=self.api_key_var)
        api_entry.grid(row=0, column=1, columnspan=3, sticky="ew", pady=6)
        ttk.Button(form, text="Сохранить ключ", command=self.save_api_key).grid(row=0, column=4, padx=(8, 0), pady=6)

        ttk.Label(form, text="Из валюты").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=6)
        from_box = ttk.Combobox(form, textvariable=self.from_currency_var, values=COMMON_CURRENCIES, state="readonly")
        from_box.grid(row=1, column=1, sticky="ew", pady=6)

        ttk.Label(form, text="В валюту").grid(row=1, column=2, sticky="w", padx=(16, 8), pady=6)
        to_box = ttk.Combobox(form, textvariable=self.to_currency_var, values=COMMON_CURRENCIES, state="readonly")
        to_box.grid(row=1, column=3, sticky="ew", pady=6)

        ttk.Label(form, text="Сумма").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=6)
        amount_entry = ttk.Entry(form, textvariable=self.amount_var)
        amount_entry.grid(row=2, column=1, sticky="ew", pady=6)

        ttk.Button(form, text="Конвертировать", command=self.convert_currency).grid(row=2, column=3, sticky="e", pady=6)
        ttk.Button(form, text="Загрузить историю", command=self._load_history_into_table).grid(row=2, column=4, padx=(8, 0), pady=6)

        result_frame = ttk.LabelFrame(container, text="Результат", padding=14)
        result_frame.pack(fill="x", pady=(0, 12))
        self.result_label = ttk.Label(result_frame, text="Пока нет конвертации.")
        self.result_label.pack(anchor="w")
        ttk.Label(result_frame, textvariable=self.status_var, foreground="#444").pack(anchor="w", pady=(8, 0))

        table_frame = ttk.LabelFrame(container, text="История", padding=12)
        table_frame.pack(fill="both", expand=True)

        columns = ("timestamp", "from", "to", "amount", "rate", "result")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        headings = {
            "timestamp": "Дата и время",
            "from": "Из",
            "to": "В",
            "amount": "Сумма",
            "rate": "Курс",
            "result": "Результат",
        }
        widths = {"timestamp": 180, "from": 70, "to": 70, "amount": 120, "rate": 120, "result": 140}
        for col in columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=widths[col], anchor="center")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _load_saved_api_key(self) -> str:
        if SETTINGS_FILE.exists():
            try:
                data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
                return str(data.get("api_key", ""))
            except json.JSONDecodeError:
                return ""
        return os.getenv("EXCHANGERATE_API_KEY", "")

    def save_api_key(self):
        api_key = self.api_key_var.get().strip()
        if not api_key:
            messagebox.showwarning("API-ключ", "Введите API-ключ, чтобы сохранить его.")
            return

        SETTINGS_FILE.write_text(
            json.dumps({"api_key": api_key}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.status_var.set("API-ключ сохранён.")

    def convert_currency(self):
        api_key = self.api_key_var.get().strip()
        from_currency = self.from_currency_var.get().strip().upper()
        to_currency = self.to_currency_var.get().strip().upper()
        amount_text = self.amount_var.get().strip()

        if not api_key:
            messagebox.showerror("Ошибка", "Введите API-ключ ExchangeRate API.")
            return

        try:
            amount = float(amount_text.replace(",", "."))
        except ValueError:
            messagebox.showerror("Ошибка ввода", "Сумма должна быть положительным числом.")
            return

        if amount <= 0:
            messagebox.showerror("Ошибка ввода", "Сумма должна быть положительным числом.")
            return

        if from_currency == to_currency:
            messagebox.showerror("Ошибка ввода", "Выберите разные валюты для конвертации.")
            return

        url = API_URL.format(
            api_key=api_key,
            from_currency=quote(from_currency),
            to_currency=quote(to_currency),
            amount=amount,
        )

        try:
            request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(request, timeout=15) as response:
                data = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            messagebox.showerror("Сетевая ошибка", f"Не удалось получить курс: HTTP {exc.code}")
            return
        except URLError as exc:
            messagebox.showerror("Сетевая ошибка", f"Не удалось получить курс: {exc.reason}")
            return
        except ValueError:
            messagebox.showerror("Ошибка", "Сервер вернул некорректный ответ.")
            return

        if data.get("result") != "success":
            error_message = data.get("error-type", "Неизвестная ошибка API")
            messagebox.showerror("Ошибка API", f"Конвертация не выполнена: {error_message}")
            return

        rate = data.get("conversion_rate")
        result = data.get("conversion_result")
        if rate is None or result is None:
            messagebox.showerror("Ошибка", "API не вернул данные конвертации.")
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        record = {
            "timestamp": timestamp,
            "from_currency": from_currency,
            "to_currency": to_currency,
            "amount": amount,
            "rate": rate,
            "result": result,
        }

        self._append_history(record)
        self._add_history_row(record)
        self.result_label.config(
            text=f"{amount:g} {from_currency} = {result:.4f} {to_currency} (курс {rate:.6f})"
        )
        self.status_var.set("Конвертация выполнена и добавлена в историю.")

    def _append_history(self, record):
        history = self._load_history()
        history.insert(0, record)
        HISTORY_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load_history(self):
        if not HISTORY_FILE.exists():
            return []

        try:
            history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []

        if not isinstance(history, list):
            return []
        return history

    def _load_history_into_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        history = self._load_history()
        for record in history:
            self._add_history_row(record)

        self.status_var.set(f"Загружено записей истории: {len(history)}")

    def _add_history_row(self, record):
        self.tree.insert(
            "",
            "end",
            values=(
                record.get("timestamp", ""),
                record.get("from_currency", ""),
                record.get("to_currency", ""),
                self._format_number(record.get("amount")),
                self._format_number(record.get("rate")),
                self._format_number(record.get("result")),
            ),
        )

    @staticmethod
    def _format_number(value):
        try:
            number = float(value)
        except (TypeError, ValueError):
            return str(value)
        return f"{number:.4f}".rstrip("0").rstrip(".")


def main():
    root = tk.Tk()
    app = CurrencyConverterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
