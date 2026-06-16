"""
Standalone Cosmic Login demo.

A fully working, self-contained Flask app that serves ONLY the cosmic login
screen (the animated Three.js universe + the Wikipedia-powered fun-fact APIs
the page depends on). The page itself is fully interactive; the actual
authentication routes are stubbed to show "Under development".

Run:
    pip install -r requirements.txt
    python app.py
Then open http://127.0.0.1:5000/

NOTE: the bundled cosmic-login.js references its Earth textures under
"/oneos/static/...", so the Flask static endpoint is mounted there to keep the
copied JS/CSS/template byte-for-byte identical to the original app.
"""

import json
import random
import re as _re
import urllib.parse
import urllib.request

from flask import Flask, render_template, request, redirect, jsonify, Response

# static_url_path matches the hardcoded "/oneos/static/..." paths inside
# cosmic-login.js, so the asset URLs and url_for('static', ...) line up.
app = Flask(__name__, static_url_path='/oneos/static', static_folder='static')


# --------------------------------------------------------------------------- #
# Login screen + stubbed auth routes
# --------------------------------------------------------------------------- #
@app.route('/')
def index():
    return redirect('/login/cosmic')


@app.route('/login/cosmic')
def login_cosmic():
    """The one and only working page: the cosmic login screen."""
    return render_template(
        'login_cosmic.html',
        enable_real_auth=True,
        login_action_url='/login',
        google_login_url='/login/google',
        cosmic_fact_url='/api/cosmic-fact',
        cosmic_object_fact_url='/api/cosmic-object-fact',
        alternate_login_url='/login/pexel',
        alternate_login_label='Use Classic Login',
    )


@app.route('/login', methods=['GET', 'POST'])
def login():
    return Response('Under development', mimetype='text/plain')


@app.route('/login/google')
def login_google():
    return Response('Under development', mimetype='text/plain')


@app.route('/login/pexel')
def login_pexel():
    return Response('Under development', mimetype='text/plain')


# --------------------------------------------------------------------------- #
# Wikipedia-powered cosmic fun-fact APIs (the login page calls these)
# --------------------------------------------------------------------------- #
WIKI_OBJECTS = [
    # planets & moons
    "Jupiter", "Saturn", "Mars", "Neptune", "Uranus", "Venus",
    "Mercury (planet)", "Pluto", "Europa (moon)", "Titan (moon)",
    "Enceladus", "Io (moon)", "Ganymede (moon)", "Triton (moon)",
    # stars
    "Betelgeuse", "Sirius", "Vega", "Rigel", "Antares", "Polaris",
    "Aldebaran", "Proxima Centauri", "Alpha Centauri", "UY Scuti",
    # galaxies
    "Andromeda Galaxy", "Whirlpool Galaxy", "Sombrero Galaxy",
    "Pinwheel Galaxy", "Triangulum Galaxy", "Messier 87", "Milky Way",
    # nebulae & deep sky
    "Orion Nebula", "Crab Nebula", "Carina Nebula", "Helix Nebula",
    "Eagle Nebula", "Horsehead Nebula", "Ring Nebula", "Pillars of Creation",
    # exotic objects & events
    "Black hole", "Neutron star", "Pulsar", "Quasar", "Supernova",
    "Halley's Comet", "Olympus Mons", "Great Red Spot", "Rings of Saturn",
    # exoplanets
    "Kepler-452b", "TRAPPIST-1", "55 Cancri e", "HD 189733 b",
]

FALLBACK_FACTS = [
    {
        "title": "Betelgeuse",
        "type": "Red supergiant star",
        "extract": ("Betelgeuse is a red supergiant in Orion, roughly 760 times "
                    "wider than the Sun. If it sat at the centre of our solar "
                    "system, its surface would reach past the asteroid belt."),
        "image": None,
        "url": "https://en.wikipedia.org/wiki/Betelgeuse",
    },
    {
        "title": "Andromeda Galaxy",
        "type": "Spiral galaxy",
        "extract": ("The Andromeda Galaxy is the nearest major galaxy to the "
                    "Milky Way and is on a collision course with it — the two "
                    "are expected to merge in about 4.5 billion years."),
        "image": None,
        "url": "https://en.wikipedia.org/wiki/Andromeda_Galaxy",
    },
    {
        "title": "Neutron star",
        "type": "Stellar remnant",
        "extract": ("A neutron star packs more mass than the Sun into a sphere "
                    "about 20 km across. A single teaspoon of its material "
                    "would weigh around a billion tonnes on Earth."),
        "image": None,
        "url": "https://en.wikipedia.org/wiki/Neutron_star",
    },
]

WIKI_OBJECT_ALIASES = {
    "Sun": ["Sun"],
    "Mercury": ["Mercury (planet)"],
    "Venus": ["Venus"],
    "Earth": ["Earth"],
    "Moon": ["Moon"],
    "Mars": ["Mars"],
    "Jupiter": ["Jupiter"],
    "Saturn": ["Saturn"],
    "Uranus": ["Uranus"],
    "Neptune": ["Neptune"],
    "Milky Way": ["Milky Way"],
    "Andromeda Galaxy": ["Andromeda Galaxy"],
    "Orion Constellation": ["Orion (constellation)"],
    "Luna Minor": ["Subsatellite", "Natural satellite"],
    "Selene": ["Moon", "Natural satellite"],
}

WIKI_KIND_FALLBACKS = {
    "planet": ["Planet", "Exoplanet"],
    "star": ["Star"],
    "galaxy": ["Galaxy"],
    "constellation": ["Constellation"],
}


def _trim_extract(text, limit=320):
    """Trim to the last full sentence under the limit."""
    if len(text) <= limit:
        return text
    cut = text[:limit]
    dot = cut.rfind(". ")
    return (cut[: dot + 1]) if dot > 80 else cut.rsplit(" ", 1)[0] + "…"


def _fetch_wiki_summary(title):
    slug = urllib.parse.quote(title.replace(" ", "_"))
    req = urllib.request.Request(
        f"https://en.wikipedia.org/api/rest_v1/page/summary/{slug}",
        headers={"User-Agent": "CosmicLoginDemo/1.0 (educational UI demo)"},
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.load(resp)


def _pick_wiki_image(data):
    """Pick the best available Wikipedia image URL."""
    thumb = (data.get("thumbnail") or {}).get("source")
    original = (data.get("originalimage") or {}).get("source")
    image = thumb or original or ""
    if not image:
        return ""
    orig_width = (data.get("originalimage") or {}).get("width", 0)
    if thumb and orig_width:
        for width in (960, 500, 330):
            if width <= orig_width:
                return _re.sub(r"/(\d+)px-", f"/{width}px-", thumb)
    return image


def _wiki_candidates_for_object(name, type_, kind, wiki_title=""):
    """Generate likely Wikipedia titles for a clicked scene object."""
    candidates = []

    def add(value):
        value = (value or "").strip()
        if value and value not in candidates:
            candidates.append(value)

    add(wiki_title)
    for alias in WIKI_OBJECT_ALIASES.get(name, []):
        add(alias)
    add(name)

    type_map = {
        "Rocky Planet": "Planet",
        "Gas Giant": "Gas giant",
        "Ice Giant": "Ice giant",
        "Our Home World": "Earth",
        "Earth's Natural Satellite": "Moon",
        "Hypothetical Submoon": "Subsatellite",
        "Spiral Galaxy (M31)": "Andromeda Galaxy",
        "Barred Spiral Galaxy": "Milky Way",
        "G-type Main Sequence Star": "Sun",
    }
    add(type_map.get(type_, ""))
    add(type_)

    for fallback in WIKI_KIND_FALLBACKS.get((kind or "").strip().lower(), []):
        add(fallback)

    return candidates


def _search_url_for_object(name, type_=""):
    query = " ".join(part for part in [name, type_] if part).strip()
    return "https://en.wikipedia.org/wiki/Special:Search?search=" + urllib.parse.quote(query or name)


@app.route("/api/cosmic-fact-image")
def cosmic_fact_image():
    raw_url = (request.args.get("url", "") or "").strip()
    if not raw_url:
        return jsonify({"error": "Missing url"}), 400
    parsed = urllib.parse.urlparse(raw_url)
    if parsed.scheme != "https" or parsed.netloc not in {"upload.wikimedia.org", "commons.wikimedia.org"}:
        return jsonify({"error": "Unsupported image host"}), 400
    req = urllib.request.Request(
        raw_url,
        headers={"User-Agent": "CosmicLoginDemo/1.0 (educational UI demo)"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        image_bytes = resp.read()
        content_type = resp.headers.get_content_type() or "image/jpeg"
    return Response(
        image_bytes,
        mimetype=content_type,
        headers={"Cache-Control": "public, max-age=3600"},
    )


@app.route("/api/cosmic-fact")
def cosmic_fact():
    for title in random.sample(WIKI_OBJECTS, k=min(4, len(WIKI_OBJECTS))):
        try:
            data = _fetch_wiki_summary(title)
            extract = data.get("extract")
            image = _pick_wiki_image(data)
        except Exception:
            continue
        if not extract or not image:
            continue
        return jsonify({
            "title": data.get("title", title),
            "type": (data.get("description") or "Celestial object").capitalize(),
            "extract": _trim_extract(extract),
            "image": "/api/cosmic-fact-image?url=" + urllib.parse.quote(image, safe=""),
            "url": data.get("content_urls", {}).get("desktop", {}).get("page",
                   f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"),
            "source": "wikipedia",
        })
    fact = dict(random.choice(FALLBACK_FACTS))
    fact["source"] = "fallback"
    return jsonify(fact)


@app.route("/api/cosmic-object-fact")
def cosmic_object_fact():
    name = (request.args.get("name", "") or "").strip()
    type_ = (request.args.get("type", "") or "").strip()
    kind = (request.args.get("kind", "") or "").strip()
    wiki_title = (request.args.get("wikiTitle", "") or "").strip()

    if not name:
        return jsonify({"error": "Missing object name"}), 400

    for title in _wiki_candidates_for_object(name, type_, kind, wiki_title):
        try:
            data = _fetch_wiki_summary(title)
        except Exception:
            continue
        extract = data.get("extract")
        if not extract:
            continue
        image = _pick_wiki_image(data)
        return jsonify({
            "title": data.get("title", name),
            "type": (data.get("description") or type_ or "Celestial object").capitalize(),
            "extract": _trim_extract(extract),
            "image": (
                "/api/cosmic-fact-image?url=" + urllib.parse.quote(image, safe="")
                if image else None
            ),
            "url": data.get("content_urls", {}).get("desktop", {}).get("page",
                   f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"),
            "source": "wikipedia",
            "badge": "Wikipedia",
        })

    fallback_type = type_ or "Celestial object"
    fallback_name = wiki_title or name
    return jsonify({
        "title": name,
        "type": fallback_type,
        "extract": (
            f"No dedicated Wikipedia summary was found for {name}. "
            f"Open Wikipedia search to explore full pages related to this {fallback_type.lower()}."
        ),
        "image": None,
        "url": _search_url_for_object(fallback_name, fallback_type),
        "source": "search",
        "badge": "Wikipedia Search",
    })


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
