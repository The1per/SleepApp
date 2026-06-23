import re

def run():
    with open('pipeline.py', 'r', encoding='utf-8') as f:
        content = f.read()

    new_function = '''
def generate_watchpat_summary(data: dict, lang: str = "en") -> str:
    pahi = data["pAHI"]

    if lang == "he":
        if pahi < 5:
            severity = "normal"
            conclusion = "לסיכום: בדיקת השינה תקינה."
        elif pahi < 15:
            severity = "mild"
            conclusion = "לסיכום: בדיקת השינה מצביעה על הפרעת נשימה בשינה בדרגה קלה."
        elif pahi < 30:
            severity = "moderate"
            conclusion = "לסיכום: בדיקת השינה מצביעה על הפרעת נשימה בשינה בדרגה בינונית."
        elif pahi < 50:
            severity = "severe"
            conclusion = "לסיכום: בדיקת השינה מצביעה על הפרעת נשימה בשינה בדרגה חמורה."
        else:
            severity = "very severe"
            conclusion = "לסיכום: בדיקת השינה מצביעה על הפרעת נשימה בשינה בדרגה חמורה מאוד."

        if 0 < data["tst_hours"] < 4.0:
            if severity == "normal":
                conclusion = "לסיכום: משך שינה קצר (פחות מ-4 שעות), אך עדיין ניתן לסכם את בדיקת השינה כתקינה."
            else:
                conclusion += " (הערה: משך שינה קצר של פחות מ-4 שעות)."

        if data["snoring_mean_db"] > 45:
            snoring_text = f"זוהו נחירות בעוצמה של {data['snoring_mean_db']:.0f} דציבל (בינונית/חמורה)."
        elif data["snoring_mean_db"] > 0:
            snoring_text = f"זוהו נחירות בעוצמה של {data['snoring_mean_db']:.0f} דציבל (קלה)."
        else:
            snoring_text = "לא זוהו נחירות."

        summary = (
            f"תוצאות בדיקת שינה WatchPAT\\n"
            f"בדיקת שינה ביתית בוצעה באמצעות מכשיר WatchPAT\\n"
            f"תאריך בדיקת השינה: {data['date']}.\\n"
            f"זמן ניטור שינה כולל: {data['tst_hours']:.1f} שעות.\\n"
            f"יעילות שינה: {data['efficiency']:.1f}%. "
            f"מספר יקיצות: {data['wakes_per_hour']:.1f} לשעה.\\n\\n"
            f"{snoring_text}\\n\\n"
            f"אירועי נשימה (הפסקות נשימה וירידות בנשימה) נצפו בתדירות של {data['pAHI']:.1f} לשעה.\\n"
            f"אירועים המלווים בירידה בריווי החמצן נצפו בתדירות של {data['ODI']:.1f} לשעה.\\n"
            f"ריווי חמצן ממוצע: {data['mean_sat']:.0f}%. "
            f"ריווי חמצן מינימלי: {data['min_sat']:.0f}%.\\n"
            f"ריווי חמצן מתחת ל-90% נצפה במשך {data['sat_below_90_pct']:.1f}% מזמן הניטור.\\n\\n"
            f"קשר לתנוחת שינה: (נדרש פענוח ידני של טבלת תנוחות הגוף).\\n"
            f"קשר לשנת REM: (נדרש פענוח ידני של מדדי נשימה).\\n\\n"
            f"{conclusion}\\n"
            f"המלצות: המשך בירור/טיפול במסגרת מרפאת/מכון שינה.\\n"
        )
    else:
        if pahi < 5:
            severity = "normal"
            conclusion = "To summarize: the sleep study is normal."
        elif pahi < 15:
            severity = "mild"
            conclusion = "To summarize: the sleep study indicates sleep-disordered breathing of mild degree."
        elif pahi < 30:
            severity = "moderate"
            conclusion = "To summarize: the sleep study indicates sleep-disordered breathing of moderate degree."
        elif pahi < 50:
            severity = "severe"
            conclusion = "To summarize: the sleep study indicates sleep-disordered breathing of severe degree."
        else:
            severity = "very severe"
            conclusion = "To summarize: the sleep study indicates sleep-disordered breathing of very severe degree."

        if 0 < data["tst_hours"] < 4.0:
            if severity == "normal":
                conclusion = "To summarize: short sleep duration (less than 4 hours), but the sleep study can still be summarized as normal."
            else:
                conclusion += " (Note: short sleep duration of less than 4 hours)."

        if data["snoring_mean_db"] > 45:
            snoring_text = f"Snoring was detected at an intensity of {data['snoring_mean_db']:.0f} dB (Moderate/Severe)."
        elif data["snoring_mean_db"] > 0:
            snoring_text = f"Snoring was detected at an intensity of {data['snoring_mean_db']:.0f} dB (Mild)."
        else:
            snoring_text = "Snoring was not detected."

        summary = (
            f"WatchPAT sleep study results\\n"
            f"A home sleep study was performed using WatchPAT\\n"
            f"Date of the sleep study: {data['date']}.\\n"
            f"Total sleep monitoring duration: {data['tst_hours']:.1f} hours.\\n"
            f"Sleep efficiency: {data['efficiency']:.1f}%. "
            f"Number of awakenings: {data['wakes_per_hour']:.1f} per hour.\\n\\n"
            f"{snoring_text}\\n\\n"
            f"Respiratory events (apneas and hypopneas) were observed at a frequency of {data['pAHI']:.1f} per hour.\\n"
            f"Events associated with oxygen desaturation were observed at a frequency of {data['ODI']:.1f} per hour.\\n"
            f"Average saturation: {data['mean_sat']:.0f}%. "
            f"Minimum saturation: {data['min_sat']:.0f}%.\\n"
            f"Saturation below 90% for {data['sat_below_90_pct']:.1f}% of the monitoring time.\\n\\n"
            f"Association with sleep position: (Requires manual review of Body Position table).\\n"
            f"Association with REM sleep: (Requires manual review of Respiratory Indices).\\n\\n"
            f"{conclusion}\\n"
            f"Recommendations: continue evaluation/treatment within a sleep clinic/institute.\\n"
        )
    return summary
'''

    pattern = r"def generate_watchpat_summary\(data: dict\) -> str:.*?    return summary"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        content = content[:match.start()] + new_function.strip() + content[match.end():]
        print("Replaced generate_watchpat_summary successfully")
    else:
        print("Failed to replace generate_watchpat_summary")

    # Update caller in _create_docx_detailed
    # find `watchpat_summary_text = generate_watchpat_summary(watchpat_data)`
    content = content.replace(
        "watchpat_summary_text = generate_watchpat_summary(watchpat_data)",
        "watchpat_summary_text = generate_watchpat_summary(watchpat_data, lang=lang)"
    )

    with open('pipeline.py', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    run()
