"""The real Training-tab exercise pool -- replaces the generic "Activity
1/2/3" placeholders (see ui/training.py's _default_activities) with
content chosen for this specific, ENT-confirmed condition: incomplete
glottic closure causing a breathy voice and reduced pitch/loudness range
(see Investigation/01_Voice_Quality_Overview.html), with a documented
history of the voice improving during ~3-4 months of prescribed voice
therapy/Pulmo-Train practice and relapsing after stopping.

Every exercise here is drawn from established, published voice-therapy
approaches for exactly this presentation (glottic insufficiency /
hypofunctional, breathy voice), not invented:
  - Semi-Occluded Vocal Tract Exercises (SOVTE) -- straw/tube phonation,
    the category the Pulmo-Train device itself belongs to (Titze;
    Laukkanen's "LaxVox"-style water-resistance tube work). Increases
    back-pressure and promotes more efficient glottal closure with less
    effort -- the most directly evidence-matched category for this
    condition, and the one already shown (via the logged CPPS/HNR trend
    across the 2025 sessions) to have measurably helped before.
  - Vocal Function Exercises (Stemple protocol) -- warm-up/stretch/
    contract/power glides specifically designed to improve laryngeal
    muscle strength and closure coordination.
  - Resonant Voice Therapy (Verdolini) -- easy, forward-focused humming
    that promotes adequate closure without straining.
  - Breath-voice coordination (s/z ratio) -- the classic clinical
    screening contrast for glottic insufficiency, reused here as a
    therapeutic awareness drill: a healthy voice sustains "z" about as
    long as "s"; a large gap (z much shorter than s) is the textbook
    signature of air escaping through an incompletely closed glottis.
  - Twang/adduction brightness -- a controlled, non-effortful way to
    practice fuller fold adduction without the hard glottal onsets that
    therapy usually avoids.
  - Direct pitch and loudness range work, since "terrible range" was
    named specifically alongside breathiness.

This is a starting pool grounded in the general literature for this
condition, NOT a substitute for the patient's own SLP -- the exact
program the ENT/SLP prescribed for the 5 sessions that worked isn't known
here in detail, and a follow-up ENT visit is already scheduled. Treat
this as something to review with that clinician, not a finalized
prescription.

The 2026-07-14 expansion keeps every new activity short and low effort.
It is designed to be done in a supported chair with feet supported or an
easy neutral standing position, with permission to change position at any
time. That accommodates the active Stage-1 back flare and generalized
hypermobility recorded in Health's patient profile; these are voice-practice
cards, not posture-correction or physical-rehabilitation drills. See
docs/training_activity_catalogue.md for the activity rationale, recording
quality limitation, and stop rules.
"""
from __future__ import annotations

import re

from config import speech_practice_paragraph
from ui.activities import Activity, ActivityStep, SIGN_ILLUSTRATIONS

_REP_COUNT_RE = re.compile(r"\d+(?:-\d+)?\s*(?:times|rounds)\b", re.IGNORECASE)
SPEECH_PRACTICE_PARAGRAPH = speech_practice_paragraph()


def _steps(
    *instructions: str,
    speech_paragraph: str | None = None,
    paragraph_step: int | None = None,
) -> list[ActivityStep]:
    """Every Activity's instructions must guide the user by time, not a rep
    count -- Screen B (ui/activities.py) only ever runs a plain countdown,
    it never counts reps for the user, so telling them to do "N times" or
    "N rounds" is guidance the app can't back up. Say "until the timer runs
    out" (or a concrete duration) instead; the regex below rejects the old
    phrasing so a new activity can't reintroduce it by accident. A connected-
    speech activity may attach one supplied practice paragraph to one of its
    four explanation steps; this keeps the text visible during that practice
    without placing it on vowel, hum, or recovery activities."""
    if len(instructions) != 4:
        raise ValueError("Screen A is designed for exactly 4 steps per activity")
    if (speech_paragraph is None) != (paragraph_step is None):
        raise ValueError("speech_paragraph and paragraph_step must be provided together")
    if speech_paragraph is not None and not speech_paragraph.strip():
        raise ValueError("speech_paragraph must not be empty")
    if paragraph_step is not None and paragraph_step not in range(1, len(instructions) + 1):
        raise ValueError("paragraph_step must select one of the four Activity steps")
    for text in instructions:
        if _REP_COUNT_RE.search(text):
            raise ValueError(
                f"instruction must guide by time, not a rep count: {text!r} "
                '(say "until the timer runs out" instead of "N times"/"N rounds")'
            )
    return [
        ActivityStep(
            instruction=text,
            illustration=SIGN_ILLUSTRATIONS[i],
            speech_paragraph=speech_paragraph if paragraph_step == i + 1 else None,
        )
        for i, text in enumerate(instructions)
    ]


EXERCISE_LIBRARY: list[Activity] = [
    Activity(
        id="pulmo_warmup_hum",
        title="Pulmo-Train Warm-Up Hum",
        duration="3-4m",
        category="SOVT · Pulmo-Train",
        timer_seconds=180,
        steps=_steps(
            "Seal your lips gently around the Pulmo-Train mouthpiece &mdash; no clamping or pressing.",
            "Take a relaxed breath, then hum a comfortable, soft pitch through the tube for about 5 seconds.",
            "Release, rest for 2 seconds, and keep repeating the hum-and-rest cycle until the timer runs out.",
            "Keep the loudness soft to moderate throughout &mdash; this is a warm-up, not a push.",
        ),
    ),
    Activity(
        id="pulmo_pitch_glides",
        title="Pulmo-Train Pitch Glides",
        duration="4-5m",
        category="SOVT · Pulmo-Train",
        timer_seconds=240,
        steps=_steps(
            "With the tube sealed gently in your lips, take a relaxed breath.",
            "Starting at your lowest comfortable pitch, glide smoothly up to your highest comfortable pitch, like a siren.",
            "Glide back down just as smoothly to where you started, on the same breath if you can.",
            "Rest, then keep repeating the up-and-down glide until the timer runs out.",
        ),
    ),
    Activity(
        id="pulmo_water_resistance",
        title="Pulmo-Train Water Resistance",
        duration="4m",
        category="SOVT · Pulmo-Train",
        timer_seconds=240,
        steps=_steps(
            "If your Pulmo-Train has the water attachment, fill a glass and submerge the tube end 1-2cm below the surface.",
            "Take a breath and phonate a steady 'oo' through the tube to create an even stream of bubbles.",
            "Sustain the bubbling for 8-10 seconds per breath, keeping it steady rather than gasping.",
            "Rest between breaths and keep going until the timer runs out.",
        ),
    ),
    Activity(
        id="pulmo_reading_carryover",
        title="Pulmo-Train Reading Carryover",
        duration="4-5m",
        category="SOVT · Pulmo-Train",
        timer_seconds=270,
        steps=_steps(
            "Seal the tube gently in your lips and read the supplied practice paragraph aloud through it at a comfortable pitch and loudness.",
            "Focus on steady airflow and an even tone rather than volume.",
            "Remove the tube and immediately re-read the same paragraph without it.",
            "Try to carry over the same easy, connected feeling you had with the tube in.",
            speech_paragraph=SPEECH_PRACTICE_PARAGRAPH,
            paragraph_step=1,
        ),
    ),
    Activity(
        id="vfe_sustained_i",
        title="Sustained /i/ Warm-Up",
        duration="3m",
        category="Vocal Function Exercise",
        timer_seconds=180,
        steps=_steps(
            "Sit or stand tall and let your shoulders and jaw relax.",
            "Take a deep, relaxed breath in.",
            "Sustain a clear 'ee' vowel at a comfortable, soft pitch for as long as feels easy.",
            "Rest, then keep repeating until the timer runs out, noticing if your longest sustain gets a little longer.",
        ),
    ),
    Activity(
        id="vfe_ascending_glide",
        title="Ascending Glide (Stretch)",
        duration="4m",
        category="Vocal Function Exercise",
        timer_seconds=210,
        steps=_steps(
            "Take a relaxed breath in.",
            "Starting at your lowest note, glide smoothly and softly up to your highest note on 'whoop'.",
            "Keep it light the whole way up &mdash; no straining or pushing near the top.",
            "Rest, then keep repeating until the timer runs out.",
        ),
    ),
    Activity(
        id="vfe_descending_glide",
        title="Descending Glide (Firm Closure)",
        duration="4m",
        category="Vocal Function Exercise",
        timer_seconds=210,
        steps=_steps(
            "Take a relaxed breath in.",
            "Starting at your highest comfortable note, glide smoothly down to your lowest note on 'whoop'.",
            "Keep the tone connected the whole way down, without any breaks or breathiness.",
            "Rest, then keep repeating until the timer runs out.",
        ),
    ),
    Activity(
        id="resonant_humming",
        title="Resonant Humming to Forward Placement",
        duration="3m",
        category="Resonant Voice",
        timer_seconds=180,
        steps=_steps(
            "Close your lips gently and let your jaw relax.",
            "Hum 'mmm' at a comfortable pitch, feeling a light buzz on your lips and nose.",
            "Once the buzz feels easy, open into 'mmm-ah', keeping that same easy vibration as you open the vowel.",
            "Keep repeating the hum-to-vowel glide until the timer runs out.",
        ),
    ),
    Activity(
        id="breath_sz_ratio",
        title="Breath-Voice Coordination (s/z)",
        duration="3-4m",
        category="Breath Coordination",
        timer_seconds=210,
        steps=_steps(
            "Take a full, relaxed breath in.",
            "Sustain a hissing 'sss' for as long as feels comfortable, and note roughly how long it lasted.",
            "On a fresh breath, sustain a buzzing 'zzz' for as long as feels comfortable, and note that time too.",
            "Keep repeating the pair until the timer runs out &mdash; the goal over time is for the 'zzz' to last just as long as the 'sss'.",
        ),
    ),
    Activity(
        id="twang_brightness",
        title="Twang Brightness Exercise",
        duration="3m",
        category="Adduction / Brightness",
        timer_seconds=180,
        steps=_steps(
            "Say an exaggerated, nasal 'nyah-nyah-nyah', like a cartoon witch or a duck.",
            "Notice the bright, forward, slightly nasal buzz of that sound.",
            "Carry a touch of that same brightness into the first sentence of the supplied practice paragraph.",
            "Keep repeating until the timer runs out, without pushing or straining for volume.",
            speech_paragraph=SPEECH_PRACTICE_PARAGRAPH,
            paragraph_step=3,
        ),
    ),
    Activity(
        id="loudness_range_glide",
        title="Soft-to-Loud Range Glide",
        duration="3-4m",
        category="Pitch & Loudness Range",
        timer_seconds=210,
        steps=_steps(
            "Sustain a comfortable 'ah' vowel starting very softly.",
            "Gradually grow louder over about 5-6 seconds while keeping your pitch steady.",
            "Gradually fade back down to soft over another 5-6 seconds.",
            "Rest, then keep repeating until the timer runs out.",
        ),
    ),
    Activity(
        id="supported_voice_reset",
        title="Supported Voice Reset",
        duration="2m",
        category="Voice Setup",
        timer_seconds=120,
        steps=_steps(
            "Choose a chair with back support and both feet supported, or an easy neutral standing position; do not hold a corrected posture.",
            "Let your jaw, tongue, and shoulders soften, and keep the phone or text high enough that you do not lean forward.",
            "Use quiet nasal breaths, then make a soft mid-range 'mmm' only while it feels easy.",
            "Reset or change position whenever needed until the timer runs out; stop if back, throat, or breathing comfort worsens.",
        ),
    ),
    Activity(
        id="lip_trill_ease",
        title="Lip Trill Ease",
        duration="3m",
        category="SOVT / No Device",
        timer_seconds=180,
        steps=_steps(
            "Use a supported chair with your feet supported, or an easy neutral standing position; avoid holding an unfamiliar posture.",
            "Let your lips vibrate on a quiet, comfortable middle pitch with an easy stream of air.",
            "Use short trills with quiet rests; if your lips will not trill easily, skip this activity instead of pressing.",
            "Keep the sound light rather than louder or higher until the timer runs out, and stop if strain, dizziness, or back symptoms increase.",
        ),
    ),
    Activity(
        id="voiced_v_flow",
        title="Voiced /v/ Flow",
        duration="3m",
        category="SOVT / Flow Phonation",
        timer_seconds=180,
        steps=_steps(
            "Use a supported chair with your feet supported, or an easy neutral standing position; change position whenever needed.",
            "On an easy exhale, let a light 'vvv' flow into 'voo' at a comfortable middle pitch.",
            "Keep the start gentle and connected; do not hold your breath or make a hard vocal attack.",
            "Use short sound-and-rest cycles until the timer runs out, without increasing loudness; stop if throat effort builds.",
        ),
    ),
    Activity(
        id="nasal_resonance_ladder",
        title="Nasal Resonance Ladder",
        duration="3m",
        category="Resonant Voice",
        timer_seconds=180,
        steps=_steps(
            "Use a supported chair with your feet supported, or an easy neutral standing position; do not brace or hold still.",
            "Make a soft 'mmm', then 'nnn', then 'ng' as in 'sing', keeping only a light facial vibration.",
            "Let the final sound open into an easy vowel such as 'mee', with no added loudness.",
            "Rest or change position between gentle sound sequences until the timer runs out; stop if your throat or back becomes less comfortable.",
        ),
    ),
    Activity(
        id="resonant_phrase_carryover",
        title="Resonant Phrase Carryover",
        duration="3m",
        category="Functional Resonance",
        timer_seconds=180,
        steps=_steps(
            "Use a supported chair with your feet supported, or an easy neutral standing position, and use the supplied practice paragraph.",
            "Begin with a soft 'mmm', then let it lead directly into each sentence.",
            "Use a light, normal speaking volume; do not whisper, call, or push for extra volume.",
            "Pause and reset between phrases until the timer runs out, changing position or stopping if effort or back symptoms increase.",
            speech_paragraph=SPEECH_PRACTICE_PARAGRAPH,
            paragraph_step=1,
        ),
    ),
    Activity(
        id="small_step_pitch_pattern",
        title="Small-Step Pitch Pattern",
        duration="3m",
        category="Pitch Control",
        timer_seconds=180,
        steps=_steps(
            "Use a supported chair with your feet supported, or an easy neutral standing position, and choose a comfortable middle pitch.",
            "On 'oo', move one small step above that pitch, return to middle, then move one small step below it.",
            "Keep the notes separate and gentle rather than sliding, and avoid both your top and bottom range.",
            "Rest or change position between patterns until the timer runs out; stop instead of reaching for a note that feels effortful.",
        ),
    ),
    Activity(
        id="gentle_phrase_pacing",
        title="Gentle Phrase Pacing",
        duration="3m",
        category="Speech Coordination",
        timer_seconds=180,
        steps=_steps(
            "Use a supported chair with your feet supported, or an easy neutral standing position, with the supplied practice paragraph ready.",
            "Say one short phrase on an easy exhale, then pause at a natural phrase end before breathing again.",
            "Let the next breath be quiet and unforced; do not rush to finish the whole sentence on one breath.",
            "Continue the speak-and-pause pattern until the timer runs out, changing position or stopping if breathlessness, strain, or back symptoms increase.",
            speech_paragraph=SPEECH_PRACTICE_PARAGRAPH,
            paragraph_step=1,
        ),
    ),
    Activity(
        id="easy_articulation",
        title="Easy Articulation Practice",
        duration="3m",
        category="Speech Clarity",
        timer_seconds=180,
        steps=_steps(
            "Use a supported chair with your feet supported, or an easy neutral standing position, and use the supplied practice paragraph.",
            "Speak slowly and clearly, letting your lips and tongue do the work rather than getting louder.",
            "Keep pitch and volume comfortable; reduce the precision if your jaw or throat starts to catch or tire.",
            "Pause and reset between phrases until the timer runs out, with no whispering or forced projection.",
            speech_paragraph=SPEECH_PRACTICE_PARAGRAPH,
            paragraph_step=1,
        ),
    ),
    Activity(
        id="chant_to_speech_bridge",
        title="Chant-to-Speech Bridge",
        duration="3m",
        category="Functional Carryover",
        timer_seconds=180,
        steps=_steps(
            "Use a supported chair with your feet supported, or an easy neutral standing position, and use the first sentence of the supplied practice paragraph.",
            "Say that sentence on one comfortable, gentle note, like a short chant.",
            "Then say the same sentence in natural speech while keeping the same low-effort feeling.",
            "Keep alternating chant and natural speech until the timer runs out, and stop if you notice increasing strain, hoarseness, or back discomfort.",
            speech_paragraph=SPEECH_PRACTICE_PARAGRAPH,
            paragraph_step=1,
        ),
    ),
    Activity(
        id="voice_recovery_break",
        title="Brief Voice Recovery Break",
        duration="2m",
        category="Voice Recovery",
        timer_seconds=120,
        steps=_steps(
            "Choose a supported chair with your feet supported, or an easy neutral standing position; change position rather than holding still.",
            "Rest quietly and take water if you would like; do not whisper or repeatedly clear your throat.",
            "Use quiet nasal breathing and soften your jaw and shoulders while checking that both throat and back comfort stay steady.",
            "At the end, speak one easy normal sentence only if comfort stayed steady; otherwise finish with quiet rest and stop the activity.",
        ),
    ),
    Activity(
        id="cooldown_carryover",
        title="Cool-Down & Carryover Check",
        duration="1m",
        category="Cool-Down",
        timer_seconds=45,
        steps=_steps(
            "Take three slow, relaxed breaths.",
            "Hum gently for about 10 seconds at a comfortable pitch.",
            "Read the supplied practice paragraph as normal conversation, paying attention to how your voice feels.",
            "Compare that feeling to how your voice felt at the very start of this session.",
            speech_paragraph=SPEECH_PRACTICE_PARAGRAPH,
            paragraph_step=3,
        ),
    ),
]
