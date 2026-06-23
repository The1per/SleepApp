import re

def run():
    with open('pipeline.py', 'r', encoding='utf-8') as f:
        content = f.read()

    new_function = '''
def generate_watchpat_summary(data: dict, lang: str = "en") -> str:
    pahi = data.get("pAHI", 0)
    tst = data.get("tst_hours", 0)
    t90 = data.get("sat_below_90_pct", 0)
    avg_sat = data.get("mean_sat", 100)
    min_sat = data.get("min_sat", 100)

    # 1. Determine the conclusion text based on the flowchart
    if tst > 0 and tst < 4.0:
        if lang == "he":
            conclusion = "לסיכום: משך השינה היה קצר, דבר העלול להפחית את מהימנות התוצאות.\\nהערה: נדרשת בדיקת רופא (Send to review by a physician)."
        else:
            conclusion = "To summarize: the sleep duration was short, which may reduce the reliability of the results.\\nNote: Send to review by a physician."
    elif pahi < 5:
        if t90 <= 1.0 and min_sat >= 90:
            if lang == "he":
                conclusion = "לסיכום: בדיקת השינה תקינה."
            else:
                conclusion = "To summarize: the sleep study is normal."
        elif t90 > 5.0 or avg_sat < 94 or min_sat < 85:
            if lang == "he":
                conclusion = "לסיכום: בדיקת השינה מצביעה על הפרעת נשימה בשינה בדרגה קלה, עם דה-סטורציה לילית שאינה פרופורציונלית.\\nהמלצות: המשך הערכה/טיפול במסגרת מרפאת שינה."
            else:
                conclusion = "To summarize: the sleep study indicates mild sleep-disordered breathing, with disproportionate nocturnal desaturation.\\nRecommendations: continue evaluation/treatment within a sleep clinic."
        else:
            if lang == "he":
                conclusion = "לסיכום: בדיקת השינה אינה מצביעה על הפרעת נשימה משמעותית בשינה לפי קריטריון AHI. עם זאת, נצפתה ירידה בריווי החמצן בדם בלילה.\\nהמלצות: המשך הערכה/טיפול במסגרת מרפאת שינה."
            else:
                conclusion = "To summarize: the sleep study does not indicate significant sleep-disordered breathing according to AHI criteria. However, a drop in blood oxygen saturation was observed at night.\\nRecommendations: continue evaluation/treatment within a sleep clinic."
    else:
        if pahi < 15:
            if lang == "he":
                conclusion = "לסיכום: בדיקת השינה מצביעה על הפרעת נשימה בשינה בדרגה קלה.\\nהמלצות: המשך הערכה/טיפול במסגרת מרפאת שינה."
            else:
                conclusion = "To summarize: the sleep study indicates mild sleep-disordered breathing.\\nRecommendations: continue evaluation/treatment within a sleep clinic."
        elif pahi <= 30:
            if lang == "he":
                conclusion = "לסיכום: בדיקת השינה מצביעה על הפרעת נשימה בשינה בדרגה בינונית.\\nהמלצות: המשך הערכה/טיפול במסגרת מרפאת שינה."
            else:
                conclusion = "To summarize: the sleep study indicates moderate sleep-disordered breathing.\\nRecommendations: continue evaluation/treatment within a sleep clinic."
        else:
            if lang == "he":
                conclusion = "לסיכום: בדיקת השינה מצביעה על הפרעת נשימה בשינה בדרגה חמורה.\\nהמלצות: המשך הערכה/טיפול במסגרת מרפאת שינה."
            else:
                conclusion = "To summarize: the sleep study indicates severe sleep-disordered breathing.\\nRecommendations: continue evaluation/treatment within a sleep clinic."

    # 2. Format snoring
    if data.get("snoring_mean_db", 0) > 45:
        if lang == "he":
            snoring_text = f"זוהו נחירות בעוצמה של {data['snoring_mean_db']:.0f} דציבל (בינונית/חמורה)."
        else:
            snoring_text = f"Snoring was detected at an intensity of {data['snoring_mean_db']:.0f} dB (Moderate/Severe)."
    elif data.get("snoring_mean_db", 0) > 0:
        if lang == "he":
            snoring_text = f"זוהו נחירות בעוצמה של {data['snoring_mean_db']:.0f} דציבל (קלה)."
        else:
            snoring_text = f"Snoring was detected at an intensity of {data['snoring_mean_db']:.0f} dB (Mild)."
    else:
        if lang == "he":
            snoring_text = "לא זוהו נחירות."
        else:
            snoring_text = "Snoring was not detected."

    # 3. Build the final string
    if lang == "he":
        summary = (
            f"תוצאות בדיקת שינה WatchPAT\\n"
            f"בדיקת שינה ביתית בוצעה באמצעות מכשיר WatchPAT\\n"
            f"תאריך בדיקת השינה: {data.get('date', 'N/A')}.\\n"
            f"זמן ניטור שינה כולל: {tst:.1f} שעות.\\n"
            f"יעילות שינה: {data.get('efficiency', 0):.1f}%. "
            f"מספר יקיצות: {data.get('wakes_per_hour', 0):.1f} לשעה.\\n\\n"
            f"{snoring_text}\\n\\n"
            f"אירועי נשימה (הפסקות נשימה וירידות בנשימה) נצפו בתדירות של {pahi:.1f} לשעה.\\n"
            f"אירועים המלווים בירידה בריווי החמצן נצפו בתדירות של {data.get('ODI', 0):.1f} לשעה.\\n"
            f"ריווי חמצן ממוצע: {avg_sat:.0f}%. "
            f"ריווי חמצן מינימלי: {min_sat:.0f}%.\\n"
            f"ריווי חמצן מתחת ל-90% נצפה במשך {t90:.1f}% מזמן הניטור.\\n\\n"
            f"קשר לתנוחת שינה: (נדרש פענוח ידני של טבלת תנוחות הגוף).\\n"
            f"קשר לשנת REM: (נדרש פענוח ידני של מדדי נשימה).\\n\\n"
            f"{conclusion}\\n"
        )
    else:
        summary = (
            f"WatchPAT sleep study results\\n"
            f"A home sleep study was performed using WatchPAT\\n"
            f"Date of the sleep study: {data.get('date', 'N/A')}.\\n"
            f"Total sleep monitoring duration: {tst:.1f} hours.\\n"
            f"Sleep efficiency: {data.get('efficiency', 0):.1f}%. "
            f"Number of awakenings: {data.get('wakes_per_hour', 0):.1f} per hour.\\n\\n"
            f"{snoring_text}\\n\\n"
            f"Respiratory events (apneas and hypopneas) were observed at a frequency of {pahi:.1f} per hour.\\n"
            f"Events associated with oxygen desaturation were observed at a frequency of {data.get('ODI', 0):.1f} per hour.\\n"
            f"Average saturation: {avg_sat:.0f}%. "
            f"Minimum saturation: {min_sat:.0f}%.\\n"
            f"Saturation below 90% for {t90:.1f}% of the monitoring time.\\n\\n"
            f"Association with sleep position: (Requires manual review of Body Position table).\\n"
            f"Association with REM sleep: (Requires manual review of Respiratory Indices).\\n\\n"
            f"{conclusion}\\n"
        )
    return summary
'''

    pattern = r"def generate_watchpat_summary\(data: dict, lang: str = \"en\"\) -> str:.*?    return summary"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        content = content[:match.start()] + new_function.strip() + content[match.end():]
        print("Replaced generate_watchpat_summary with flowchart logic successfully")
    else:
        print("Failed to replace generate_watchpat_summary")

    with open('pipeline.py', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    run()
