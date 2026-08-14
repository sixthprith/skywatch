# Sky Watch — Central Florida

A static board for deciding whether something in the sky is worth the drive. Rockets from the Cape, Blue Angels dates, and anything else worth pointing a face at.

No backend, no build step, no API key. Drop it on GitHub Pages and it works.

---

## What's here

| File | Job |
|---|---|
| `index.html` | The whole app. Fetches live launches, reads `events.json`, computes bearing and drive time from Gainesville or Orlando. |
| `events.json` | Airshows and military events. Hand-maintained — there is no API for these. |
| `scripts/build_ics.py` | Builds `feed.ics` from live launches + `events.json`. Standard library only. |
| `.github/workflows/feed.yml` | Runs that script every 6 hours and commits the result. |

---

## Setup

1. Create a repo, push these files to `main`.
2. **Settings → Pages → Source: Deploy from a branch → `main` / root.**
3. Wait a minute. Site is live at `https://<you>.github.io/<repo>/`.
4. **Settings → Actions → General → Workflow permissions → Read and write.** Without this the feed job can't commit.
5. Run the workflow once by hand (Actions tab → Rebuild calendar feed → Run workflow) to generate `feed.ics`.

## Getting actual notifications

The site can't push to your phone — static pages have no way to reach you. The calendar feed can.

In Google Calendar on desktop: **Other calendars → + → From URL**, paste:

```
https://<you>.github.io/<repo>/feed.ics
```

Every event carries a 3-hour reminder. Google re-polls the URL periodically (usually every several hours, sometimes up to a day — this is Google's cadence, not something the repo controls), so new launches appear on their own. Set the calendar's notification defaults once and your phone does the rest.

For same-day scrub awareness, nothing beats [@SpaceflightNow](https://spaceflightnow.com/launch-schedule/) or the launch provider's own stream — a T-2h scrub won't propagate through a calendar feed fast enough to save you a drive.

## Adding an event

Append to `events.json`:

```json
{
  "id": "unique-slug",
  "type": "airshow",
  "name": "Event name",
  "detail": "What makes it worth going.",
  "venue": "Where",
  "lat": 28.5, "lon": -81.3,
  "start": "2027-03-14",
  "end": "2027-03-15",
  "confidence": "confirmed",
  "cost": "Free",
  "url": "https://..."
}
```

`type` is `airshow` or `military`. Military entries render with a dashed amber rule down the left edge. Push, and the feed job picks it up on the next push automatically.

## Where the data comes from

**Launches** — [The Space Devs Launch Library 2](https://thespacedevs.com/llapi), free and unauthenticated. Anonymous access is capped at roughly 15 requests per hour per IP; the page makes exactly one per load, so this only bites if you're hammering refresh. The site filters to Florida pads by matching the pad's location name.

**Airshows** — no API exists. The Blue Angels publish a PDF; the Thunderbirds publish a separate page; the two sometimes disagree. Everything currently in `events.json` was pulled from the official schedules and the trade press, with 2027 dates marked preliminary because the confirmed version isn't announced until ICAS in December 2026.

**Military tests and flyovers** — no public feed at all, by design. Worth watching manually: Patrick SFB and Eglin release advisories, and the FAA's temporary flight restriction list often telegraphs something interesting before an announcement does.

## The sky conditions layer

Off by default. Hit **Sky conditions** and the page makes one request to the Aviation Weather Center for current METARs at ten reporting stations, then annotates each event with the nearest one. Nothing loads until you switch it on, and it only loads once per session.

Each event gets a flight category — VFR, MVFR, IFR, LIFR — in the standard aviation colors, plus a plain-language read of what the cloud layers mean *for watching*, which is a different question than what they mean for landing. A scattered deck at 3,000 feet is comfortably VFR and will still hide a rocket.

**If the layer refuses to load:** the AWC may not send the `Access-Control-Allow-Origin` header, which means a browser on your domain isn't allowed to read the response. Enough people have built proxies for this API that I'd assume it doesn't, but it's untested here — flip the switch and find out. The page says so plainly if it fails.

The fallback, if it does: add a step to `.github/workflows/feed.yml` that curls the METAR endpoint and writes `wx.json` into the repo, then point `loadWeather()` at that file instead. Server-to-server requests have no CORS restriction, so it just works. The cost is staleness — a six-hour cron gives you six-hour-old weather, which is close to useless. Better to run that job every 20 minutes, or drop the layer to `api.weather.gov`, which does send CORS headers and will work directly from the browser today.

## Two things the site guesses

**Drive time** is distance ÷ 55 mph plus 15 minutes. It ignores I-4, which is a meaningful omission for anything south of Orlando.

**"Visible from home"** flags a launch when it's within 220 miles and lifting off between 8 PM and 6 AM Eastern. That's the window where a rocket reads as a slow bright star climbing out of the east. Daytime launches from the same distance are invisible. It's a heuristic — high-energy trajectories and clear nights beat it, overcast defeats it.

## Ideas worth building next

- Cloud cover at the pad and at your location, from the National Weather Service API (free, no key). The single biggest predictor of a wasted drive.
- A viewing-spot layer — Playalinda, Jetty Park, the Max Brewer Bridge — with which pads each one has line of sight to.
- Pull the launch azimuth so the compass points where the rocket will actually *go*, not just where the pad sits.
