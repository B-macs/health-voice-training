"""Single source of truth for app language/locale.

Two independent knobs, since they don't have to move together:
- UI_LANGUAGE: every interface string (tab labels, buttons, status words,
  metric display names) -- purely cosmetic, change freely for the reader.
- ANALYSIS_LANGUAGE: the continuous-speech reading passage and the AVQI/ABI
  norm cutoffs in analysis/norms.py, both of which are validated per
  language -- changing this changes what's measured/judged, not just how
  it's labeled, so it stays independent of UI_LANGUAGE.
"""
from __future__ import annotations

UI_LANGUAGE = "en"
ANALYSIS_LANGUAGE = "de"

# Recordings are grouped by the user's local date, rather than the UTC date
# of the Streamlit server. Change this explicitly before recording while
# travelling; the chosen value is persisted with each new analysis.
USER_TIMEZONE = "Europe/Berlin"

# The established Voice Quality calculation is intentionally retained as a
# personal acoustic-trend baseline. A version makes future presentation or
# calibration changes auditable instead of silently reinterpreting history.
VOICE_QUALITY_SCORING_VERSION = "voice_quality_v1"

READING_PASSAGE_IDS = {
    "de": "de_nordwind_und_sonne_opening_v1",
}

READING_PASSAGES = {
    "de": (
        "Einst stritten sich Nordwind und Sonne, wer von ihnen beiden wohl "
        "der Stärkere wäre, als ein Wanderer."
    ),
}
"""Opening clause of the standard IPA-Handbook 'parallel text' passage
("Nordwind und Sonne", the public-domain Aesop fable translation used
internationally as a phonetically-balanced reading passage; full text
cross-verified against an academic phonetics source, Uni Stuttgart IMS
"Sprache und Gehirn" tutorial). Deliberately shortened to match the
reference VOXplot desktop app's own excerpt and its ~10s fixed recording
window (see ui/capture.py) -- the full multi-sentence fable takes 30-45s to
read, far longer than that window."""

UI_STRINGS = {
    "de": {
        "page_title": "Voxplot Aufnahme",
        "title": "Sprachprobenaufnahme",
        "caption": (
            "Nehmen Sie den nachhaltigen Vokal [a:] und einen kurzen "
            "Lesetext auf (oder laden Sie eine .wav-Datei hoch). Die "
            "Ergebnisse werden protokolliert, nicht angezeigt."
        ),
        "tab_sv": "1. Nachhaltiger Vokal [a:]",
        "tab_cs": "2. Lesetext",
        "sv_record_label": "Nachhaltigen Vokal aufnehmen",
        "sv_upload_label": "...oder .wav-Datei hochladen",
        "cs_record_label": "Lesetext aufnehmen",
        "cs_upload_label": "...oder .wav-Datei hochladen",
        "waiting_prefix": "Es fehlt noch: ",
        "waiting_sv": "nachhaltiger Vokal",
        "waiting_cs": "Lesetext",
        "analyze_button": "Analysieren & protokollieren",
        "success": "Aufgenommen und protokolliert.",
        "error": "Analyse fehlgeschlagen -- Details siehe QA (Debug) unten.",
        "qa_expander": "Technischer Aufnahmebericht",
        "qa_no_run": "In dieser Sitzung wurde noch keine Analyse durchgeführt.",

        # --- Dashboard shell ---
        "app_name": "VOXplot",
        "app_version": "v2.4.0",
        "tab_training": "TRAINING",
        "tab_voice_analysis": "STIMMANALYSE",
        "tab_details": "DETAILS",
        "new_recording_button": "Neue Aufnahme",

        # --- Training tab ---
        "training_daily_plan_title": "Tagesplan",
        "training_help_aria": "Hilfe",
        "training_help_text": "Schließe jede Aktivität ab, um dein tägliches Energieziel zu erreichen und deine Serie am Leben zu halten.",
        "training_status_complete": "Abgeschlossen",
        "training_start_button": "Starten",
        "training_recording_category": "Aufnahme",
        "training_day_of_label": "Tag {day} von {total}",
        "training_plan_complete_title": "10-Tage-Basisprogramm abgeschlossen!",
        "training_plan_complete_body": "Gut durchgehalten. Sieh dir im Tab \"Details\" an, wie sich dein Trend über diese 10 Tage entwickelt hat -- das ist die Basis, auf der ein längeres Programm aufbauen kann.",
        "training_day_complete_title": "Heutiges Training abgeschlossen!",
        "training_day_complete_body": "Gut gemacht. Der nächste Tag deines Plans wird morgen freigeschaltet.",

        # --- Hero / composite score ---
        "hero_title": "Stimmqualität",
        "hero_subtitle": "Persönlicher akustischer Trend — keine Diagnose",
        "hero_recipe": "50 % Gesamtindex · 50 % Behauchtheits-Schätzung",
        "recording_quality_label": "Aufnahmequalität",
        "quality_usable": "vergleichbar",
        "quality_limited": "eingeschränkt",
        "quality_not_usable": "nicht verwertbar",
        "quality_legacy_unknown": "Altbestand / unbekannt",
        "score_not_available": "Nicht bewertet",
        "status_optimal": "Referenznah",
        "status_attention": "Nahe Referenzgrenze",
        "status_concerning": "Außerhalb Referenzbereich",
        "prev_week_label": "Vorwoche Ø",
        "prev_month_label": "Vormonat Ø",

        # --- Trend card ---
        "trend_card_title": "Gesamt-Stimmqualität",
        "trend_card_subtitle": "30-Tage-Trend",
        "trend_monthly_label": "MONATSTREND",

        # --- Acoustic insights ---
        "insights_title": "Akustische Einblicke",
        "insights_current": "Aktuell",
        "insights_week_avg": "Wo. Ø",
        "insights_month_avg": "Mo. Ø",
        "friendly_pitch_group": "Tonhöhenstabilität",

        # --- Voice profile radar ---
        "profile_title": "Stimmprofil",
        "profile_cluster_hoarseness": "Heiserkeit",
        "profile_cluster_breathiness": "Behauchtheit",
        "legend_current": "Aktuell",
        "legend_week_avg": "Wochenmittel",
        "legend_month_avg": "Monatsmittel",
        "verdict_optimal": "Persönlicher Trend liegt nahe den konfigurierten Referenzbereichen.",
        "verdict_attention": "Einige Werte liegen nahe einer Referenzgrenze. Vergleichen Sie nur gleichartige, qualitätsgeprüfte Aufnahmen.",
        "verdict_concerning": "Mehrere Werte liegen außerhalb der konfigurierten Referenzbereiche. Dies ist keine Diagnose.",

        # --- Details tab ---
        "details_group_hoarseness": "Heiserkeit",
        "details_group_breathiness": "Behauchtheit",
        "details_group_general": "Allgemein",
        "details_indices_title": "Indizes",
        "trend_toggle_day": "Tag",
        "trend_toggle_week": "Woche",
        "trend_toggle_month": "Monat",
        "trend_select_metric": "Parameter auswählen",
        "trend_norm_line": "Referenzgrenze",
        "no_history": "Noch keine früheren Sitzungen protokolliert.",
        "trend_protocol_note": "Der Trend enthält nur Aufnahmen mit demselben Protokoll und derselben Bewertungslogik.",

        # --- Capture flow ---
        "capture_cancel": "Abbrechen",
        "capture_next": "Weiter",
        "capture_waveform_title": "Aufnahme-Wellenform",
        "capture_trim_instruction": "Mindestens 3 Sekunden der Zieläußerung auswählen",
        "capture_protocol_hint": "VOXplot analysiert daraus ein qualitätsgeprüftes 3-Sekunden-Fenster. Ruhiger Raum, gleicher Abstand und dasselbe Gerät verbessern Trends.",
        "capture_selection_too_short": "Die Auswahl muss mindestens 3 Sekunden lang sein.",
        "capture_play_all": "Alles abspielen",
        "capture_play_selection": "Auswahl abspielen",
        "capture_record_again": "Erneut aufnehmen",
        "capture_accept": "Übernehmen",
        "capture_accepted_label": "Übernommen",
        "capture_load_error": "Audiodatei konnte nicht gelesen werden -- bitte erneut versuchen.",
        "capture_too_short": "Aufnahme zu kurz -- bitte erneut aufnehmen.",
        "capture_sv_title": "Aufnahme starten und Vokal halten",
        "capture_cs_title": "Aufnahme starten und Text vorlesen",
        "capture_text_to_record_label": "Zu lesender Text",
        "capture_vowel_prompt": "...aaaaaa...",
        "capture_analyzing_message": "Deine Stimmprobe wird analysiert und protokolliert...",
        "capture_congrats_title": "Gut gemacht!",
        "capture_congrats_subtitle": "Deine Stimmprobe wurde analysiert und gespeichert.",
        "capture_view_results_button": "Ergebnisse ansehen",

        # --- Activity screens: explanation (A), timed practice (B),
        # results (C) -- see ui/activities.py ---
        "activity_continue_button": "Weiter",
        "activity_timer_reminder_heading": "Zur Erinnerung",
        "activity_timer_label": "Verbleibende Zeit",
        "activity_results_tab": "ERGEBNISSE",
        "activity_audios_tab": "AUDIOS",
        "activity_complete_heading": "Übung abgeschlossen!",
        "activity_complete_subtext": "Gut gemacht. Genau das ist die Übung, die sich beim nächsten wichtigen Gespräch auszahlt.",
        "activity_metric_placeholder_label": "Messwert",
        "activity_done_button": "Fertig",
    },
    "en": {
        "page_title": "Voxplot Recording",
        "title": "Voice Sample Recording",
        "caption": (
            "Record the sustained vowel [a:] and a short reading passage "
            "(or upload a .wav file). Results are logged, not displayed."
        ),
        "tab_sv": "1. Sustained Vowel [a:]",
        "tab_cs": "2. Reading Passage",
        "sv_record_label": "Record sustained vowel",
        "sv_upload_label": "...or upload a .wav file",
        "cs_record_label": "Record reading passage",
        "cs_upload_label": "...or upload a .wav file",
        "waiting_prefix": "Still missing: ",
        "waiting_sv": "sustained vowel",
        "waiting_cs": "reading passage",
        "analyze_button": "Analyze & log",
        "success": "Recorded and logged.",
        "error": "Analysis failed -- see QA (Debug) below for details.",
        "qa_expander": "Technical recording report",
        "qa_no_run": "No analysis has been run yet in this session.",

        # --- Dashboard shell ---
        "app_name": "VOXplot",
        "app_version": "v2.4.0",
        "tab_training": "TRAINING",
        "tab_voice_analysis": "VOICE ANALYSIS",
        "tab_details": "DETAILS",
        "new_recording_button": "New Recording",

        # --- Training tab ---
        "training_daily_plan_title": "Daily plan",
        "training_help_aria": "Help",
        "training_help_text": "Complete each activity to hit your daily energy goal and keep your streak alive.",
        "training_status_complete": "Complete",
        "training_start_button": "Start",
        "training_recording_category": "Recording",
        "training_day_of_label": "Day {day} of {total}",
        "training_plan_complete_title": "10-Day Baseline Complete!",
        "training_plan_complete_body": "Nice work sticking with it. Head to the Details tab to see how your trend moved over these 10 days -- that's the baseline a longer program can build on.",
        "training_day_complete_title": "Today's Training Complete!",
        "training_day_complete_body": "Nice work. The next day of your plan unlocks tomorrow.",

        # --- Hero / composite score ---
        "hero_title": "Voice Quality",
        "hero_subtitle": "Personal acoustic trend — not a diagnosis",
        "hero_recipe": "50% overall acoustic index · 50% breathiness estimate",
        "recording_quality_label": "Recording quality",
        "quality_usable": "comparable",
        "quality_limited": "limited",
        "quality_not_usable": "not usable",
        "quality_legacy_unknown": "legacy / unknown",
        "score_not_available": "Not scored",
        "status_optimal": "Reference-aligned",
        "status_attention": "Near reference boundary",
        "status_concerning": "Outside reference range",
        "prev_week_label": "Prev. Week Avg",
        "prev_month_label": "Prev. Month Avg",

        # --- Trend card ---
        "trend_card_title": "Overall Voice Quality",
        "trend_card_subtitle": "30-Day Trend",
        "trend_monthly_label": "MONTHLY TREND",

        # --- Acoustic insights ---
        "insights_title": "Acoustic Insights",
        "insights_current": "Current",
        "insights_week_avg": "Wk. Avg",
        "insights_month_avg": "Mo. Avg",
        "friendly_pitch_group": "Pitch Stability",

        # --- Voice profile radar ---
        "profile_title": "Voice Profile",
        "profile_cluster_hoarseness": "Hoarseness",
        "profile_cluster_breathiness": "Breathiness",
        "legend_current": "Current",
        "legend_week_avg": "Weekly Avg",
        "legend_month_avg": "Monthly Avg",
        "verdict_optimal": "Your personal trend is close to the configured reference ranges.",
        "verdict_attention": "Some values are near a reference boundary. Compare only like-for-like, quality-checked recordings.",
        "verdict_concerning": "Several values are outside the configured reference ranges. This is not a diagnosis.",

        # --- Details tab ---
        "details_group_hoarseness": "Hoarseness",
        "details_group_breathiness": "Breathiness",
        "details_group_general": "General",
        "details_indices_title": "Indices",
        "trend_toggle_day": "Day",
        "trend_toggle_week": "Week",
        "trend_toggle_month": "Month",
        "trend_select_metric": "Select parameter",
        "trend_norm_line": "Reference cutoff",
        "no_history": "No previous sessions logged yet.",
        "trend_protocol_note": "The trend contains only recordings with the same protocol and scoring version.",

        # --- Capture flow ---
        "capture_cancel": "Cancel",
        "capture_next": "Next",
        "capture_waveform_title": "Recording Waveform",
        "capture_trim_instruction": "Select at least 3 seconds of the target utterance",
        "capture_protocol_hint": "VOXplot analyzes a quality-checked 3-second window from this selection. A quiet room, consistent distance, and the same device improve trends.",
        "capture_selection_too_short": "The selection must be at least 3 seconds long.",
        "capture_play_all": "Play All",
        "capture_play_selection": "Play Selection",
        "capture_record_again": "Record again",
        "capture_accept": "Accept",
        "capture_accepted_label": "Accepted",
        "capture_load_error": "Couldn't read that audio file -- please try again.",
        "capture_too_short": "Recording too short -- please record again.",
        "capture_sv_title": "Start recording and sustain vowel sound",
        "capture_cs_title": "Start recording and read this text",
        "capture_text_to_record_label": "Text to record",
        "capture_vowel_prompt": "...aaaaaa...",
        "capture_analyzing_message": "Analyzing and logging your voice sample...",
        "capture_congrats_title": "Well done!",
        "capture_congrats_subtitle": "Your voice sample has been analyzed and logged.",
        "capture_view_results_button": "View results",

        # --- Activity screens: explanation (A), timed practice (B),
        # results (C) -- see ui/activities.py ---
        "activity_continue_button": "Continue",
        "activity_timer_reminder_heading": "As a reminder",
        "activity_timer_label": "Time remaining",
        "activity_results_tab": "RESULTS",
        "activity_audios_tab": "AUDIOS",
        "activity_complete_heading": "Practice Complete!",
        "activity_complete_subtext": "Nice work. The next time a conversation actually matters, this is the practice that quietly shows up for you.",
        "activity_metric_placeholder_label": "Metric",
        "activity_done_button": "Done",
    },
}

# Metadata for every logged parameter/index: display label (in UI_LANGUAGE),
# unit, and which radar/details cluster it belongs to. Single source of
# truth so the dashboard, the details table, and the radar chart never
# drift apart.
METRIC_META = {
    "f0_mean_hz": {"label": "Mean sustained-vowel F0", "unit": "Hz", "group": "general"},
    "f0_sd_hz": {"label": "Pitch Variation", "unit": "Hz", "group": "general"},
    "f0_sd_st": {"label": "Pitch Variation", "unit": "semitones", "group": "general"},
    "jitter_local_pct": {"label": "Jitter (local)", "unit": "%", "group": "hoarseness"},
    "jitter_ppq5_pct": {"label": "Jitter (ppq5)", "unit": "%", "group": "hoarseness"},
    "shimmer_local_pct": {"label": "Shimmer (local)", "unit": "%", "group": "hoarseness"},
    "shimmer_local_db": {"label": "Shimmer (local)", "unit": "dB", "group": "hoarseness"},
    "shimmer_apq11_pct": {"label": "Shimmer (apq11)", "unit": "%", "group": "hoarseness"},
    "hnr_db": {"label": "Harmonic-to-Noise-Ratio", "unit": "dB", "group": "hoarseness"},
    "cpps_sv_db": {"label": "CPPS (Vowel)", "unit": "dB", "group": "breathiness"},
    "cpps_cs_db": {"label": "CPPS (Reading Passage)", "unit": "dB", "group": "breathiness"},
    "ltas_slope_db": {"label": "LTAS Slope", "unit": "dB", "group": "general"},
    "ltas_tilt_db": {"label": "LTAS Tilt", "unit": "dB", "group": "general"},
    "gne": {"label": "GNE", "unit": "", "group": "breathiness"},
    "h1_h2_db": {"label": "H1-H2", "unit": "dB", "group": "breathiness"},
    "avqi": {"label": "AVQI-like overall index", "unit": "", "group": "hoarseness"},
    "abi": {"label": "Voxplot breathiness estimate", "unit": "", "group": "breathiness"},
}

# The Voice Profile hexagon's 6 axes, in plotting order (see ui/svg_components.py),
# split evenly between the Hoarseness cluster (left half) and Breathiness
# cluster (right half) -- matches the reference VOXplot layout.
RADAR_AXES = ["avqi", "hnr_db", "jitter_ppq5_pct", "abi", "gne", "cpps_sv_db"]

# The established Voice Quality score (0-100, higher = better) is a personal
# trend baseline: 50% AVQI-like overall acoustic index + 50% custom Voxplot
# breathiness estimate. It deliberately does not add raw inputs again, since
# both component indices already contain overlapping acoustic information.
COMPOSITE_METRICS = ["avqi", "abi"]

# Domain cards are descriptive one-metric reference indicators, not a second
# diagnostic composite. This avoids double-counting jitter/shimmer/CPPS and
# duplicate Hz/semitone pitch variation in the interface.
GROUP_SCORE_METRICS = {
    "hoarseness": ["avqi"],
    "breathiness": ["abi"],
    "general": ["f0_sd_st"],
}

STATUS_THRESHOLDS = {"optimal": 80, "attention": 50}  # score >= optimal -> Optimal; >= attention -> Attention; else Concerning


def t(key: str, language: str = UI_LANGUAGE) -> str:
    """Look up a UI string for the given (or app-default) language."""
    return UI_STRINGS[language][key]


def reading_passage(language: str = ANALYSIS_LANGUAGE) -> str:
    return READING_PASSAGES[language]


def metric_label(key: str) -> str:
    meta = METRIC_META.get(key, {})
    label = meta.get("label", key)
    unit = meta.get("unit", "")
    return f"{label} ({unit})" if unit else label
