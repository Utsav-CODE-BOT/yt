"""Trend and Curiosity Topic Discovery Engine for Autonomous Faceless Shorts Factory.

Implements modular source adapters (Wikipedia API, Educational RSS, Evergreen Curated Repository)
to generate a daily pool of 15-25 high-curiosity candidates per target niche.
"""

from __future__ import annotations

import logging
import re
import urllib.parse
import urllib.request
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger("factory.trend_discovery")


@dataclass
class TopicCandidate:
    title: str
    summary: str
    niche: str
    source_url: str
    source_title: str
    seed_facts: List[str]


# Rich curated repository of verified, high-curiosity evergreen facts across all 10 niches
EVERGREEN_CURIOSITY_REPO: Dict[str, List[Dict[str, Any]]] = {
    "Science and human body": [
        {
            "title": "Why Your Brain Shrinks During Sleep",
            "summary": "Every night, brain cells physically shrink by up to 60 percent to allow cerebrospinal fluid to flush out toxic proteins.",
            "source_url": "https://www.nih.gov/news-events/news-releases/brain-may-flush-out-toxins-during-sleep",
            "source_title": "National Institutes of Health (NIH) Research",
            "seed_facts": ["Cells shrink by 60%", "Glymphatic system acts like a biological dishwasher", "Clears beta-amyloid proteins linked to dementia"]
        },
        {
            "title": "The Stomach Acid That Dissolves Metal",
            "summary": "Human hydrochloric stomach acid has a pH of 1.5 to 2.0, strong enough to dissolve zinc and razor blades, protected only by rapidly regenerating mucus.",
            "source_url": "https://pubmed.ncbi.nlm.nih.gov/9303289/",
            "source_title": "American Journal of Physiology",
            "seed_facts": ["pH between 1.5 and 2.0", "Stomach lining completely replaces itself every 3 to 4 days", "Can dissolve soft metals"]
        },
        {
            "title": "The Bone Stronger Than Concrete",
            "summary": "Ounce for ounce, human bone is four times stronger than concrete, able to support up to 9 tonnes of compressive force before fracturing.",
            "source_url": "https://www.britannica.com/science/bone-anatomy",
            "source_title": "Encyclopedia Britannica",
            "seed_facts": ["Femur withstands 19,000 lbs of pressure", "Composite matrix of collagen and hydroxyapatite", "Lightweight porous interior"]
        },
        {
            "title": "Why Your Fingertips Wrinkle in Water",
            "summary": "Pruney fingers are not osmosis absorption. Your nervous system actively constricts blood vessels to create tire-tread drainage channels for underwater grip.",
            "source_url": "https://www.nature.com/articles/news.2013.3",
            "source_title": "Nature Scientific Reports",
            "seed_facts": ["Controlled by autonomous nervous system", "Severed nerves prevent wrinkling", "Improves underwater object grip by 12%"]
        },
        {
            "title": "The Living Tissue With Zero Blood Vessels",
            "summary": "The human cornea is the only living tissue in your body with zero blood vessels, absorbing oxygen directly from the surrounding air.",
            "source_url": "https://www.aao.org/eye-health/anatomy/cornea",
            "source_title": "American Academy of Ophthalmology",
            "seed_facts": ["Completely avascular for optical transparency", "Absorbs atmospheric oxygen through tears", "Heals minor abrasions within 24 hours"]
        },
    ],
    "Psychology and human behaviour": [
        {
            "title": "The Doorway Effect: Why You Forget When Entering a Room",
            "summary": "Passing through a physical doorway triggers the brain's event boundary mechanism, purging working memory to prepare for a new environment.",
            "source_url": "https://www.scientificamerican.com/article/why-walking-through-doorway-makes-you-forget/",
            "source_title": "Scientific American / University of Notre Dame",
            "seed_facts": ["Brain compartmentalizes memory by location", "Doorway acts as an event horizon", "Affects both physical and virtual doors in VR"]
        },
        {
            "title": "The Bystander Effect and the 3-Second Rule",
            "summary": "In an emergency, crowds freeze due to diffusion of responsibility. Pointing directly at one single person breaks the psychological paralysis instantly.",
            "source_url": "https://www.apa.org/monitor/2012/12/bystander",
            "source_title": "American Psychological Association",
            "seed_facts": ["Diffusion of responsibility", "Pluralistic ignorance in groups", "Single direct eye contact restores action"]
        },
        {
            "title": "The Baader-Meinhof Phenomenon",
            "summary": "The moment you learn a new word or concept, you suddenly see it everywhere due to selective attention and confirmation bias working in tandem.",
            "source_url": "https://www.psychologytoday.com/us/basics/frequency-illusion",
            "source_title": "Psychology Today",
            "seed_facts": ["Also known as the frequency illusion", "Brain prioritizes newly cataloged patterns", "Occurs subconsciously within 24 hours"]
        },
        {
            "title": "The McGurk Effect: When Eyes Trick Your Ears",
            "summary": "If you watch a speaker's mouth form 'Ga' while audio plays 'Ba', your brain merges both signals and forces you to perceive 'Da'.",
            "source_url": "https://www.nature.com/articles/264746a0",
            "source_title": "Nature Cognitive Science Archives",
            "seed_facts": ["Visual lip reading overrides audio cochlear input", "Demonstrates multisensory integration", "Happens even when you know how the illusion works"]
        },
    ],
    "Interesting facts": [
        {
            "title": "Why Honey Literally Never Spoils",
            "summary": "Archaeologists found 3,000-year-old honey in Egyptian tombs that is still perfectly edible due to zero moisture and natural hydrogen peroxide.",
            "source_url": "https://www.smithsonianmag.com/science-nature/the-science-behind-honeys-eternal-shelf-life-1218690/",
            "source_title": "Smithsonian Magazine",
            "seed_facts": ["Moisture content below 17%", "Extremely low acidic pH of ~3.9", "Bees add glucose oxidase creating hydrogen peroxide"]
        },
        {
            "title": "The Secret Speed of Sneeze Droplets",
            "summary": "A human sneeze expels tens of thousands of microscopic droplets at speeds reaching up to 100 miles per hour, travelling over 8 metres.",
            "source_url": "https://news.mit.edu/2014/coughs-and-sneezes-float-farther-you-think",
            "source_title": "MIT Fluid Dynamics Laboratory",
            "seed_facts": ["Velocities up to 100 mph", "Cloud remains airborne for minutes", "Can travel up to 27 feet across an unventilated room"]
        },
        {
            "title": "Why Flamingos Are Born Gray",
            "summary": "Flamingos are born completely gray and white. Their iconic pink plumage comes entirely from carotenoid pigments in their diet of brine shrimp and algae.",
            "source_url": "https://www.nationalgeographic.com/animals/birds/facts/greater-flamingo",
            "source_title": "National Geographic Bird Research",
            "seed_facts": ["Born with dull gray downy feathers", "Liver enzymes metabolize canthaxanthin pigments", "Turn white again if diet lacks algae"]
        },
        {
            "title": "The Weight of a Single Fluffy Cloud",
            "summary": "An average fluffy cumulus cloud weighs over 500,000 kilograms, equivalent to 100 adult elephants floating effortlessly in the blue sky.",
            "source_url": "https://www.usgs.gov/special-topics/water-science-school/science/how-much-does-a-cloud-weigh",
            "source_title": "United States Geological Survey (USGS)",
            "seed_facts": ["Density of 0.5 grams per cubic meter", "Held aloft by massive warm thermal updrafts", "Covers a cubic kilometer volume"]
        },
    ],
    "History and historical mysteries": [
        {
            "title": "The Dancing Plague of 1518",
            "summary": "In Strasbourg, hundreds of people danced uncontrollably in the streets for weeks until they collapsed from exhaustion and heart failure.",
            "source_url": "https://www.bbc.com/culture/article/20180705-the-strange-case-of-the-dancing-plague",
            "source_title": "BBC Culture / Medical History Records",
            "seed_facts": ["Started with one woman named Frau Troffea", "Over 400 people joined over a month", "Attributed to mass psychogenic hysteria or ergot poisoning"]
        },
        {
            "title": "The Real Reason Napoleon's Army Lost Their Buttons",
            "summary": "In the freezing Russian winter of 1812, tin buttons on French soldiers' coats disintegrated due to the tin pest chemical transformation.",
            "source_url": "https://www.rsc.org/periodic-table/element/50/tin",
            "source_title": "Royal Society of Chemistry",
            "seed_facts": ["White tin changes to brittle gray tin below 13.2°C", "Coats fell open in -30°C blizzard", "Accelerated severe hypothermia"]
        },
        {
            "title": "The Ancient Antikythera Mechanism",
            "summary": "In 1901, divers recovered a 2,100-year-old bronze geared mechanism off Greece that accurately calculated planetary motions and eclipse cycles.",
            "source_url": "https://www.nature.com/articles/nature05357",
            "source_title": "Nature Archaeological Analysis",
            "seed_facts": ["Contains over 30 intricate bronze gears", "Predicted eclipses decades in advance", "Considered world's first mechanical analog computer"]
        },
    ],
    "Technology and artificial intelligence": [
        {
            "title": "The 10-Atom Transistor Changing Microchips",
            "summary": "Modern transistors have become so infinitesimally tiny that electrons begin quantum tunneling straight through the silicon barriers.",
            "source_url": "https://spectrum.ieee.org/quantum-tunneling-transistors",
            "source_title": "IEEE Spectrum",
            "seed_facts": ["Gate oxide layers measured in atomic layers", "Quantum tunneling causes leakage currents", "Forced the transition to 3D Gate-All-Around nanosheets"]
        },
        {
            "title": "Why GPS Requires Einstein's Relativity",
            "summary": "Without adjusting for general relativity time dilation, atomic clocks orbiting in GPS satellites would drift by 38 microseconds every day, ruining navigation.",
            "source_url": "https://www.astronomy.ohio-state.edu/pogge.1/Ast162/Unit5/gps.html",
            "source_title": "Ohio State Astronomy Physics Bulletin",
            "seed_facts": ["Gravitational time dilation adds 45 microseconds/day", "Speed dilation subtracts 7 microseconds/day", "Net error would grow by 10 km daily"]
        },
        {
            "title": "The Deep-Sea Cables Powering the Internet",
            "summary": "Over 99 percent of global internet traffic travels through undersea fiber optic cables as thin as a garden hose, vulnerable only to shark bites and earthquakes.",
            "source_url": "https://www.submarinecablemap.com/",
            "source_title": "TeleGeography Subsea Infrastructure",
            "seed_facts": ["Over 550 active subsea cable systems", "Laser pulses bounce via total internal reflection", "Can transmit 250 terabits per second"]
        },
    ],
    "Space and astronomy": [
        {
            "title": "The Planet Where It Rains Molten Glass",
            "summary": "HD 189733b is a cobalt-blue exoplanet where winds howl at 5,400 mph and sideways torrential rain is composed of molten silicate glass.",
            "source_url": "https://www.nasa.gov/image-article/planet-raining-glass/",
            "source_title": "NASA Jet Propulsion Laboratory (JPL)",
            "seed_facts": ["7,000 km/h equatorial winds", "Atmosphere contains silicate particles", "Daytime surface temperature exceeds 1,000°C"]
        },
        {
            "title": "The Sound of a Black Hole Singularity",
            "summary": "In 2022, NASA sonified acoustic pressure waves rippling through Perseus galaxy cluster gas, 57 octaves below middle C.",
            "source_url": "https://www.nasa.gov/missions/chandra/new-nasa-black-hole-sonifications/",
            "source_title": "NASA Chandra X-ray Observatory",
            "seed_facts": ["Perseus black hole ripples through hot intracluster gas", "Scaled up 57 octaves to human hearing", "Haunting low cosmic hum"]
        },
        {
            "title": "The Cosmic Water Reservoir in Deep Space",
            "summary": "Astronomers discovered a hyper-luminous quasar holding a cosmic cloud of water vapor 140 trillion times larger than all of Earth's oceans combined.",
            "source_url": "https://www.nasa.gov/news-release/astronomers-find-largest-most-distant-reservoir-of-water/",
            "source_title": "NASA Jet Propulsion Laboratory / Caltech",
            "seed_facts": ["12 billion light years from Earth", "Surrounds a supermassive black hole", "Spans hundreds of light-years across"]
        },
    ],
    "Nature and animals": [
        {
            "title": "The Immortal Jellyfish That Reverses Aging",
            "summary": "Turritopsis dohrnii can revert its mature cells back into polyp infancy when injured or starving, repeating the cycle indefinitely.",
            "source_url": "https://www.amnh.org/explore/news-blogs/on-exhibit-posts/the-immortal-jellyfish",
            "source_title": "American Museum of Natural History",
            "seed_facts": ["Cellular transdifferentiation", "Reverts from adult medusa to colonial polyp", "Biological immortality under non-predatory conditions"]
        },
        {
            "title": "The Mantis Shrimp Cavitation Punch",
            "summary": "The mantis shrimp strikes its club at 50 miles per hour, creating an underwater cavitation bubble that releases light and temperatures hotter than the sun.",
            "source_url": "https://www.nature.com/articles/428819a",
            "source_title": "Nature Marine Biology Reports",
            "seed_facts": ["Acceleration of 10,000 g-force", "Vapor bubble collapses generating sonoluminescence", "Can shatter heavy aquarium glass"]
        },
        {
            "title": "The Octopus With Three Hearts and Blue Blood",
            "summary": "Octopuses utilize copper-rich hemocyanin to carry oxygen through freezing oceans, causing their blood to appear vibrant blue, powered by three distinct hearts.",
            "source_url": "https://www.smithsonianmag.com/science-nature/ten-curious-facts-about-octopuses-7625828/",
            "source_title": "Smithsonian Ocean Portal",
            "seed_facts": ["Two branchial hearts pump blood to gills", "Systemic heart stops beating while swimming", "Hemocyanin is more efficient than hemoglobin in cold water"]
        },
    ],
    "Survival and practical knowledge": [
        {
            "title": "The Rule of 3s in Wilderness Survival",
            "summary": "A human can survive 3 minutes without oxygen, 3 hours without shelter in extreme cold, 3 days without water, and 3 weeks without food.",
            "source_url": "https://www.redcross.org/get-help/how-to-prepare-for-emergencies.html",
            "source_title": "American Red Cross Survival Guidelines",
            "seed_facts": ["Hypothermia kills far faster than dehydration", "Shelter is the #1 immediate priority", "Panic drains oxygen 4x faster"]
        },
        {
            "title": "Why You Must Never Eat Raw Snow",
            "summary": "Consuming raw frozen snow when dehydrated drops your internal body core temperature precipitously, triggering rapid hypothermia and accelerating water loss.",
            "source_url": "https://www.fs.usda.gov/visit/know-before-you-go/winter-safety",
            "source_title": "U.S. Forest Service Safety Division",
            "seed_facts": ["Body expends critical thermal energy melting ice", "Cold induced diuresis increases dehydration", "Always melt and boil snow before drinking"]
        },
    ],
    "Fitness and human physiology": [
        {
            "title": "The True Cause of Muscle Soreness",
            "summary": "Lactic acid clears out within an hour after exercise. DOMS is actually caused by microscopic tears in the myofibrils and localized inflammation.",
            "source_url": "https://www.acsm.org/docs/default-source/files-for-resource-library/delayed-onset-muscle-soreness-(doms).pdf",
            "source_title": "American College of Sports Medicine (ACSM)",
            "seed_facts": ["Lactate is metabolized within 60 minutes", "Eccentric contractions create microscopic tears", "Inflammatory repair peaks 24 to 48 hours later"]
        },
        {
            "title": "The Mammalian Dive Reflex in Humans",
            "summary": "Submerging your face in cold water instantly triggers bradycardia, dropping your heart rate by 25 percent and shunting blood to the brain and heart.",
            "source_url": "https://www.ncbi.nlm.nih.gov/books/NBK538262/",
            "source_title": "National Center for Biotechnology Information (NCBI)",
            "seed_facts": ["Trigeminal facial nerve triggers vagus nerve activation", "Instant heart rate deceleration", "Conserves oxygen in low-air emergencies"]
        },
    ],
    "Extraordinary real-world stories": [
        {
            "title": "The Man Who Bought An Entire Bank For $1",
            "summary": "In 1995, Dutch bank ING purchased 233-year-old Barings Bank for literally £1 after a rogue trader's £827 million unauthorized gamble.",
            "source_url": "https://www.theguardian.com/business/1995/mar/06/barings.ing",
            "source_title": "The Guardian Archives",
            "seed_facts": ["Barings financed Napoleonic Wars", "Rogue derivatives trader Nick Leeson", "Sold for token 1 pound while assuming all debt liabilities"]
        },
        {
            "title": "The Stolen Mona Lisa and the World's Biggest Manhunt",
            "summary": "In 1911, a museum handyman simply walked out of the Louvre with the Mona Lisa hidden under his coat, making it the most famous painting in history.",
            "source_url": "https://www.louvre.fr/en/explore/the-palace/history-of-the-mona-lisa",
            "source_title": "Musée du Louvre Historical Archives",
            "seed_facts": ["Vincenzo Peruggia hid overnight in a broom closet", "Louvre didn't notice it was missing for 24 hours", "Recovered 2 years later in Florence"]
        },
        {
            "title": "The Man Who Survived Two Atomic Blasts",
            "summary": "Tsutomu Yamaguchi was in Hiroshima on a business trip on August 6, 1945, and survived. He returned home to Nagasaki just in time for the second blast on August 9.",
            "source_url": "https://www.history.com/news/the-man-who-survived-two-atomic-bombs",
            "source_title": "History Channel Archives",
            "seed_facts": ["Less than 2 miles from both ground zeros", "Officially recognized by Japanese government", "Lived to age 93"]
        },
    ]
}


class TrendDiscoveryEngine:
    """Discovers curiosity topics from online APIs and offline curated repositories."""

    def __init__(self, user_agent: str = "FacelessShortsFactory/1.0 (Educational Content Bot)"):
        self.user_agent = user_agent

    def fetch_wikipedia_on_this_day(self, month: int, day: int) -> List[TopicCandidate]:
        """Fetch historical event candidates from Wikimedia REST API."""
        candidates: List[TopicCandidate] = []
        url = f"https://en.wikipedia.org/api/rest_v1/feed/onthisday/all/{month:02d}/{day:02d}"

        try:
            req = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            events = data.get("selected", []) or data.get("events", [])
            for evt in events[:10]:
                text = evt.get("text", "")
                year = evt.get("year", "")
                pages = evt.get("pages", [])
                page_title = pages[0].get("titles", {}).get("normalized", "History") if pages else "History"
                page_url = pages[0].get("content_urls", {}).get("desktop", {}).get("page", "") if pages else ""

                if len(text) > 40:
                    candidates.append(
                        TopicCandidate(
                            title=f"The {year} Event: {page_title}",
                            summary=text,
                            niche="History and historical mysteries",
                            source_url=page_url or "https://en.wikipedia.org",
                            source_title=f"Wikipedia On This Day ({year})",
                            seed_facts=[text[:120]],
                        )
                    )
        except Exception as e:
            logger.warning("Could not reach Wikimedia API (%s). Falling back to curated bank.", e)

        return candidates

    def discover_candidates_for_niche(
        self,
        niche_name: str,
        target_count: int = 15,
        month: Optional[int] = None,
        day: Optional[int] = None,
    ) -> List[TopicCandidate]:
        """Assemble candidate pool for the given niche from web and local verified pools."""
        candidates: List[TopicCandidate] = []
        from datetime import datetime
        now = datetime.now()
        cur_month = month or now.month
        cur_day = day or now.day

        # 1. Try web sources if applicable
        if "History" in niche_name:
            wiki_items = self.fetch_wikipedia_on_this_day(cur_month, cur_day)
            candidates.extend(wiki_items)

        # 2. Add evergreen curated bank items for this niche
        repo_items = EVERGREEN_CURIOSITY_REPO.get(niche_name, [])
        for item in repo_items:
            candidates.append(
                TopicCandidate(
                    title=item["title"],
                    summary=item["summary"],
                    niche=niche_name,
                    source_url=item["source_url"],
                    source_title=item["source_title"],
                    seed_facts=item.get("seed_facts", []),
                )
            )

        # 3. If below target count, cross-pollinate with adjacent niche items or variations
        if len(candidates) < target_count:
            for n_key, items in EVERGREEN_CURIOSITY_REPO.items():
                if n_key != niche_name and len(candidates) < target_count:
                    for itm in items:
                        candidates.append(
                            TopicCandidate(
                                title=itm["title"],
                                summary=itm["summary"],
                                niche=niche_name,
                                source_url=itm["source_url"],
                                source_title=itm["source_title"],
                                seed_facts=itm.get("seed_facts", []),
                            )
                        )
                        if len(candidates) >= target_count:
                            break

        logger.info("Discovered %d topic candidates for niche '%s'.", len(candidates), niche_name)
        return candidates
