"""make_demo.py - builds demo_folder/ with FAKE files for testing and the demo.

Every name, number and detail here is made up. Run again any time to reset:
    python make_demo.py
"""
import os
import random
import shutil
import time

import docx
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo_folder")
DAY = 86400


def pdf(path, title, lines):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    c = canvas.Canvas(path, pagesize=A4)
    c.setTitle(title)
    c.setCreator("ClearTrace demo")
    c.setFont("Helvetica-Bold", 16)
    c.drawString(60, 780, title)
    c.setFont("Helvetica", 11)
    y = 750
    for line in lines:
        c.drawString(60, y, line)
        y -= 20
    c.save()


def word(path, title, lines):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    d = docx.Document()
    d.add_heading(title, 1)
    for line in lines:
        d.add_paragraph(line)
    d.save(path)


def text(path, body):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)


def blob(path, mb, seed):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    rnd = random.Random(seed)
    with open(path, "wb") as f:
        f.write(rnd.randbytes(int(mb * 1024 * 1024)))


def copy(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)


def age(path, days):
    t = time.time() - days * DAY
    os.utime(path, (t, t))


def p(*parts):
    return os.path.join(ROOT, *parts)


def main(root=None):
    global ROOT
    if root:
        ROOT = root
    if os.path.exists(ROOT):
        shutil.rmtree(ROOT)

    # ---------- Sensitive (all FAKE) ----------
    pdf(p("Downloads", "scan_0042.pdf"), "PAYSLIP - SAMPLE ONLY", [
        "Employee: Alex Sample        Employer: Bean There Cafe Pty Ltd",
        "Pay period: 01/03/2024 - 14/03/2024",
        "Gross pay: $1,842.50         Tax withheld: $312.00",
        "Net pay: $1,530.50           Superannuation: $211.89",
        "Paid to BSB 000-000  Account number 12345678",
        "THIS IS A FAKE DOCUMENT GENERATED FOR TESTING",
    ])
    copy(p("Downloads", "scan_0042.pdf"), p("Desktop", "scan_0042.pdf"))
    age(p("Downloads", "scan_0042.pdf"), 730)
    age(p("Desktop", "scan_0042.pdf"), 700)

    pdf(p("Downloads", "passport_details.pdf"), "PASSPORT DETAILS - SPECIMEN", [
        "SPECIMEN - NOT A REAL DOCUMENT",
        "Surname: SAMPLE     Given names: ALEX",
        "Nationality: AUSTRALIAN",
        "Date of birth: 01 JAN 2000",
        "Passport number: X0000000 (fake)",
    ])
    age(p("Downloads", "passport_details.pdf"), 540)

    word(p("Downloads", "Statement_March.docx"), "Bank Statement - SAMPLE", [
        "Sample Bank Ltd - bank statement for March",
        "Account name: Alex Sample   BSB: 000-000   Account number: 87654321",
        "Opening balance $2,104.33   Closing balance $1,876.10",
        "FAKE DATA FOR TESTING ONLY",
    ])
    age(p("Downloads", "Statement_March.docx"), 400)

    # Tanda angle: staff onboarding paperwork left on a manager's laptop
    pdf(p("Documents", "Staff onboarding", "TFN_declaration_J_Citizen.pdf"),
        "Tax file number declaration - SAMPLE", [
            "Payee: Jordan Citizen (FAKE)",
            "Tax file number: 000 000 000 (fake)",
            "Date of birth: 15/06/2001",
            "Employer: Bean There Cafe Pty Ltd",
            "FAKE STAFF ONBOARDING FORM FOR TESTING",
        ])
    age(p("Documents", "Staff onboarding", "TFN_declaration_J_Citizen.pdf"), 300)

    word(p("Documents", "Staff onboarding", "New_starter_Priya.docx"), "New starter form - SAMPLE", [
        "Name: Priya Example (FAKE)   Date of birth: 03/09/1999",
        "Bank: BSB 000-000  Account number 11112222",
        "Driver licence number: 00000000 (fake)",
    ])
    age(p("Documents", "Staff onboarding", "New_starter_Priya.docx"), 200)

    # ---------- Uni files + duplicates ----------
    pdf(p("QUT", "DSB201", "DSB201 Week 8 Lecture.pdf"), "DSB201 Week 8 Lecture", [
        "Data Science for Business - Week 8",
        "Topic: Classification and model evaluation",
        "Confusion matrix, precision, recall, ROC curves",
    ])
    copy(p("QUT", "DSB201", "DSB201 Week 8 Lecture.pdf"), p("Downloads", "DSB201 Week 8 Lecture.pdf"))
    copy(p("QUT", "DSB201", "DSB201 Week 8 Lecture.pdf"), p("Downloads", "DSB201 Week 8 Lecture (1).pdf"))

    pdf(p("QUT", "DSB201", "DSB201 Week 7 Lecture.pdf"), "DSB201 Week 7 Lecture", [
        "Data Science for Business - Week 7", "Topic: Regression",
    ])

    word(p("QUT", "CAB201", "Assignment_Final.docx"), "CAB201 Assignment - Final", [
        "Programming Principles - Assignment 2", "Student: Alex Sample",
        "Report on object-oriented design of a parking simulator.",
    ])
    copy(p("QUT", "CAB201", "Assignment_Final.docx"), p("Downloads", "Assignment_Final.docx"))
    copy(p("QUT", "CAB201", "Assignment_Final.docx"), p("Desktop", "Assignment_Final.docx"))

    # A big wasted duplicate (fake video) so "MB freed" is visible
    blob(p("Desktop", "orientation_recording.mp4"), 6, seed=1)
    copy(p("Desktop", "orientation_recording.mp4"), p("Downloads", "orientation_recording.mp4"))
    age(p("Downloads", "orientation_recording.mp4"), 420)

    # ---------- Normal files ----------
    text(p("Documents", "notes.txt"), "Things to do: groceries, gym, call mum.\n")
    text(p("Documents", "recipes.txt"), "Pancakes: 1 cup flour, 1 egg, 1 cup milk.\n")
    text(p("Documents", "shopping_list.txt"), "Milk, bread, eggs, coffee beans.\n")
    word(p("QUT", "MXB107", "Week 3 notes.docx"), "MXB107 Week 3", ["Probability distributions."])
    word(p("QUT", "IML", "Project ideas.docx"), "IML project ideas", ["Image classifier for plants."])
    pdf(p("Downloads", "concert_ticket.pdf"), "Concert ticket", ["Gate B, Row 12, Seat 4"])
    pdf(p("Downloads", "Gym_timetable.pdf"), "Gym timetable", ["Mon: Spin 6am", "Wed: Yoga 7pm"])
    text(p("Desktop", "todo.md"), "# Hackathon\n- build ClearTrace\n- practise demo\n")
    blob(p("Downloads", "holiday_photo.jpg"), 2.5, seed=2)
    blob(p("Downloads", "old_installer.zip"), 4, seed=3)
    age(p("Downloads", "old_installer.zip"), 900)
    age(p("Downloads", "Gym_timetable.pdf"), 500)

    n = sum(len(files) for _, _, files in os.walk(ROOT))
    print(f"Created {n} fake files in {ROOT}")
    return ROOT


if __name__ == "__main__":
    main()
