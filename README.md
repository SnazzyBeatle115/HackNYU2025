# Conscience AI — HackNYU 2025

A tiny, relentless accountability coach that keeps you focused. Tell Conscience AI your goal, and it starts a focus session, monitoring your screen and attention in real time. The moment you drift, it nudges you back—often with a friendly (or firm) voice line.

## Inspiration

We're all horrible at getting things done. Even when we want to focus, it's far too easy to get sidetracked—whether it’s a phone notification, a Wikipedia rabbit hole, or a “quick” League of Legends match that turns into an hour. Traditional productivity tools rely on self-discipline; Conscience AI adds something stronger: accountability.

## What it does

- Starts a focus session based on your stated goal
- Monitors high-level screen context to detect task drift (locally)
- Estimates attention from lightweight webcam signals
- Gives real-time voice nudges when you fall off task

It’s like having a mentor sitting on your shoulder making sure you follow through on your intentions.

## How we built it

- On-device screen monitoring to extract high-level context without storing user data
- Lightweight attention tracking via the webcam (no raw video leaves your machine)
- A real-time feedback loop powered by an LLM that generates gentle (or firm) voice nudges using ElevenLabs
- Flask backend + browser client for capture and coaching loop

## Challenges we ran into

- Balancing accountability with privacy (no screenshots/webcam frames sent to servers)
- False positives in early models (it yelled at us while we were working)
- Smooth voice interaction that’s effective without feeling annoying—or creepy
- Calibrating for different working styles (multitaskers vs deep-focus)
- Background noise sensitivity for voice interactions

## Accomplishments we're proud of

- Built a fully functional, on-device, real-time accountability loop in under 48 hours
- Effective attention tracking with minimal hardware requirements
- Early user testing shows reduced distraction events

## What we learned

- Accountability beats fancy productivity features—people work better when something is watching (respectfully)
- Attention is messy and personal; one-size-fits-all doesn’t work
- Small, immediate feedback breaks distraction loops
- Privacy-by-design is essential; users trust tools that respect boundaries

## What's next for Conscience AI

- Adaptive coaching modes: “supportive,” “strict,” or “dead serious”
- Calendar/notebook/task integrations to auto-start focus sessions
- Mobile companion for phone distraction detection
- Deeper analytics: heatmaps of distractor patterns, personalized recommendations
- End-to-end encryption + local LLM options for even stronger privacy

## Built With

- Python, Flask
- JavaScript, HTML, CSS
- OpenRouter (LLM)
- ElevenLabs (voice)
- GitHub Copilot

## Try it out

[dopaminedetoxandmakeyourselfaccountable67.tech](https://dopaminedetoxandmakeyourselfaccountable67.tech)

---

## Dev quickstart (local)

```bash
# Windows PowerShell (recommended)
pip install pipenv
pipenv install
pipenv run flask run
```

### Environment variables

- `ML_SERVER_URL` (default: `http://localhost:8081`) — target ML server used by the Flask app


Project structure (simplified):

```text
HackNYU2025/
├── app.py
├── templates/
├── static/
└── ml/
```
