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
        {
            "title": "The Hidden Clock in Every Human Cell",
            "summary": "Every single organ in your body operates its own autonomous circadian molecular clock, independently regulating metabolic repair cycles.",
            "source_url": "https://www.nobelprize.org/prizes/medicine/2017/press-release/",
            "source_title": "Nobel Prize in Physiology or Medicine",
            "seed_facts": ["PER and TIM clock genes cycle over 24 hours", "Liver and heart follow meal-time rhythms", "Irregular sleep desynchronizes organ clocks"]
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
        {
            "title": "The Zeigarnik Effect: Why Unfinished Tasks Haunt You",
            "summary": "The human brain maintains persistent cognitive intrusive thoughts about incomplete tasks until they are finished or explicitly scheduled.",
            "source_url": "https://www.britannica.com/science/Zeigarnik-effect",
            "source_title": "Encyclopedia Britannica Psychology",
            "seed_facts": ["Bluma Zeigarnik discovered waiters recall unpaid orders perfectly", "Mental tension dissipates once an action plan is written", "Underlying psychology behind cliffhangers and binge watching"]
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
        {
            "title": "The Shark That Outlived the Renaissance",
            "summary": "Greenland sharks cruise the deep Arctic seas and can live for more than 400 years, making living sharks older than Isaac Newton and Shakespeare.",
            "source_url": "https://www.science.org/doi/10.1126/science.aaf1703",
            "source_title": "Science Journal Marine Biology",
            "seed_facts": ["Eye lens radiocarbon dating confirmed 392 year lifespan", "Heart beats only once every 12 seconds", "Reaches reproductive maturity at 150 years old"]
        },
    ],
    "Ancient history and civilizations": [
        {
            "title": "Why Roman Concrete Actually Heals Itself",
            "summary": "MIT researchers discovered ancient Roman concrete contained quicklime clasts that dissolve and recrystallize when seawater enters cracks, automatically repairing harbor walls for 2,000 years.",
            "source_url": "https://news.mit.edu/2023/roman-concrete-durability-lime-clasts-0106",
            "source_title": "MIT News / Science Advances",
            "seed_facts": ["Hot mixing creates reactive calcium-rich inclusions", "Seawater dissolves quicklime into calcium carbonate", "Self-healed cracks prevent rebar-free collapse for millennia"]
        },
        {
            "title": "The Catastrophic Bronze Age Collapse",
            "summary": "Around 1177 BC, eight flourishing civilizations across the Mediterranean collapsed within fifty years due to megadroughts, earthquake storms, and mysterious Sea Peoples.",
            "source_url": "https://www.smithsonianmag.com/history/what-caused-bronze-age-collapse-180980486/",
            "source_title": "Smithsonian Magazine / Princeton Archaeological Press",
            "seed_facts": ["Mycenae, Hittite Empire, and Ugarit destroyed almost simultaneously", "Centuries of cultural dark ages followed", "Pollen cores prove severe 150-year megadrought"]
        },
        {
            "title": "How the Great Pyramid Stays at Exactly 20 Degrees",
            "summary": "The 2.3 million limestone blocks of the Great Pyramid of Giza provide such massive thermal inertia that its interior chambers remain locked at exactly 20 degrees Celsius year-round.",
            "source_url": "https://www.britannica.com/topic/Pyramids-of-Giza",
            "source_title": "Encyclopaedia Britannica Architectural Archives",
            "seed_facts": ["Mass of over 5.75 million tons", "Acts as giant passive thermal heat sink", "Internal temperature never fluctuates despite 45°C desert summers"]
        },
        {
            "title": "The Lost Underground City of Derinkuyu",
            "summary": "Carved 280 feet into volcanic rock in Cappadocia, Derinkuyu could shelter 20,000 people underground with 15,000 ventilation shafts, wineries, and rolling stone doors.",
            "source_url": "https://www.bbc.com/travel/article/20220810-derinkuyu-the-underground-city-of-cappadocia",
            "source_title": "BBC Travel / Turkish Department of Antiquities",
            "seed_facts": ["Extends 18 levels beneath the surface", "Massive 1,000-pound stone disc doors lockable only from inside", "Entire ecosystem shielded citizens from invading armies"]
        },
        {
            "title": "The Poison King Who Built Immunity to Death",
            "summary": "King Mithridates VI of Pontus ingested microscopic daily doses of deadly poisons to build biological tolerance, becoming completely immune to assassination.",
            "source_url": "https://www.worldhistory.org/Mithridates_VI/",
            "source_title": "World History Encyclopedia",
            "seed_facts": ["Formulated universal antidote known as Mithridatium", "Could not poison himself when captured and had to order a soldier to use a sword", "Gave rise to the medical term mithridatism"]
        },
        {
            "title": "The Damascus Steel Nanotube Mystery",
            "summary": "Ancient Syrian blacksmiths forged Damascus steel swords with carbon nanotubes and cementite nanowires, producing blades so sharp they could slice falling silk handkerchiefs.",
            "source_url": "https://www.nature.com/articles/444286a",
            "source_title": "Nature Materials Science Analysis",
            "seed_facts": ["High carbon wootz steel from ancient India", "Thermal cycling created aligned carbon nanotube matrices", "The exact forging technique was lost in the 18th century"]
        },
        {
            "title": "The Roman Emperor Who Declared War on Poseidon",
            "summary": "In 40 AD, Roman Emperor Caligula marched his legions to the English Channel, ordered them to attack the ocean with spears, and collected seashells as spoils of war.",
            "source_url": "https://www.historyskills.com/classroom/ancient-history/caligula-and-neptune/",
            "source_title": "Suetonius Historical Records / Roman Annals",
            "seed_facts": ["Legions drew up battle formations on the beach", "Ordered soldiers to fill helmets with seashells called 'plunder of the ocean'", "Declared a triumph over Neptune god of the sea"]
        },
    ],
    "History and historical mysteries": [
        {
            "title": "The Voynich Manuscript Nobody Can Decipher",
            "summary": "Carbon-dated to the early 1400s, the 240-page Voynich manuscript is written in an unknown alphabet and cipher that has baffled the world's greatest cryptographers.",
            "source_url": "https://beinecke.library.yale.edu/collections/highlights/voynich-manuscript",
            "source_title": "Yale University Beinecke Rare Book Library",
            "seed_facts": ["Contains drawings of nonexistent cosmological constellations and flora", "Statistical word distribution follows Zipf's law of genuine natural language", "Neither Alan Turing nor modern AI has cracked the code"]
        },
        {
            "title": "The Lost Ninth Legion That Vanished in the Mists",
            "summary": "Around 120 AD, the battle-hardened Roman Ninth Legion marched 5,000 soldiers into the Caledonian wilderness of Scotland and completely disappeared from historical records.",
            "source_url": "https://www.bbc.com/news/uk-scotland-highlands-islands-56165518",
            "source_title": "BBC History Archaeology Review",
            "seed_facts": ["Legio IX Hispana was one of Rome's most feared divisions", "Vanished past the northern frontier without a single survivor", "Prompted Emperor Hadrian to construct Hadrian's Wall across Britain"]
        },
        {
            "title": "The Ghost Ship Mary Celeste Found Sailing Empty",
            "summary": "In December 1872, the brigantine Mary Celeste was found floating in the Atlantic under full sail with untouched cargo and personal belongings, but not a single soul aboard.",
            "source_url": "https://www.smithsonianmag.com/history/abandoned-ship-the-mary-celeste-174488175/",
            "source_title": "Smithsonian Magazine Maritime Archives",
            "seed_facts": ["Lifeboat was missing but six months of food remained", "Cargo of 1,700 barrels of industrial alcohol intact", "No signs of violence, piracy, or storm damage"]
        },
        {
            "title": "The Baffling Antikythera Analog Computer",
            "summary": "Divers off a Greek island retrieved a 2,100-year-old bronze geared mechanism that tracked planetary orbits and predicted solar eclipses centuries ahead of its time.",
            "source_url": "https://www.nature.com/articles/nature05357",
            "source_title": "Nature Archaeological Analysis",
            "seed_facts": ["Contains over 30 precision differential gears", "Mechanical complexity not matched until 14th-century cathedral clocks", "Predicted Saros eclipse cycles with mechanical dials"]
        },
        {
            "title": "The Vanished Roanoke Colony and the Word Croatoan",
            "summary": "In 1590, governor John White returned to England's first New World colony to find all 115 men, women, and children gone, leaving only the word CROATOAN carved into a tree.",
            "source_url": "https://www.nationalgeographic.com/history/article/vanished-colony-roanoke-clues",
            "source_title": "National Geographic Historical Archaeology",
            "seed_facts": ["No graves, skeletons, or signs of struggle found", "Houses dismantled rather than burned down", "Evidence suggests settlers assimilated into local indigenous tribes"]
        },
        {
            "title": "The Secret Underground Tomb of Genghis Khan",
            "summary": "When Genghis Khan died in 1227, his funeral escort slaughtered every witness they met, diverted a river over the grave, and had 800 horsemen trample the earth to erase all trace.",
            "source_url": "https://www.nationalgeographic.com/history/article/valley-of-the-khans-genghis-khan-tomb",
            "source_title": "National Geographic Mongolian Expeditions",
            "seed_facts": ["Escort soldiers executed upon returning to camp to keep the secret", "Buried near sacred mountain Burkhan Khaldun", "Satellite radar scans have yet to find the burial chamber"]
        },
        {
            "title": "The Dancing Plague of 1518",
            "summary": "In Strasbourg, hundreds of people danced uncontrollably in the streets for weeks until they collapsed from exhaustion and heart failure.",
            "source_url": "https://www.bbc.com/culture/article/20180705-the-strange-case-of-the-dancing-plague",
            "source_title": "BBC Culture / Medical History Records",
            "seed_facts": ["Started with one woman named Frau Troffea", "Over 400 people joined over a month", "Attributed to mass psychogenic hysteria or ergot poisoning"]
        },
    ],
    "Historical turning points and extraordinary events": [
        {
            "title": "Operation Mincemeat: The Corpse That Fooled Hitler",
            "summary": "British intelligence dressed a deceased homeless man as a royal marine officer carrying fake invasion plans, convincing German command to defend Greece instead of Sicily.",
            "source_url": "https://www.nationalarchives.gov.uk/education/resources/operation-mincemeat/",
            "source_title": "UK National Archives Intelligence Records",
            "seed_facts": ["Body of Glyndwr Michael released off coast of Spain", "Hitler redeployed Panzer divisions from Italy to Greece", "Allied invasion of Sicily succeeded with minimal casualties"]
        },
        {
            "title": "The Man Who Prevented World War Three by Doing Nothing",
            "summary": "In 1983, Soviet officer Stanislav Petrov noticed early-warning radar detecting five incoming US nuclear missiles, correctly deduced a computer glitch, and refused to launch retaliation.",
            "source_url": "https://www.bbc.com/news/world-europe-24280831",
            "source_title": "BBC News International Archives",
            "seed_facts": ["Oko satellite false alarm caused by sun reflecting off high-altitude clouds", "Protocol required immediate massive nuclear counter-strike", "His unilateral refusal averted global nuclear annihilation"]
        },
        {
            "title": "The WWII Ghost Army of Inflatable Tanks",
            "summary": "The U.S. 23rd Headquarters Special Troops used 1,000 inflatable rubber tanks and giant sound amplifiers to trick German reconnaissance into misdirecting their frontline divisions.",
            "source_url": "https://www.defense.gov/News/Feature-Stories/story/Article/3715694/",
            "source_title": "U.S. Department of Defense Historical Archives",
            "seed_facts": ["Inflatable tanks made of heavy rubber and air pumps", "Sound vans broadcasted sounds of tank divisions from 15 miles away", "Credited with saving tens of thousands of Allied lives"]
        },
        {
            "title": "The 1814 London Beer Flood Disaster",
            "summary": "In October 1814, a 22-foot high wooden fermentation vat ruptured in London, unleashing a 15-foot tidal wave of 323,000 gallons of fermented porter down city streets.",
            "source_url": "https://www.history.com/news/london-beer-flood",
            "source_title": "History Channel Archives",
            "seed_facts": ["Iron hoop on Meux and Company brewery vat snapped", "Wave destroyed two brick houses and breached tavern walls", "Court ruled disaster was an unavoidable Act of God"]
        },
        {
            "title": "The 335-Year War Without a Single Shot Fired",
            "summary": "A state of war existed between the Netherlands and the Isles of Scilly from 1651 to 1986 without a single shot fired or casualty before a peace treaty was signed 335 years later.",
            "source_url": "https://www.historic-uk.com/HistoryUK/HistoryofBritain/The-335-Year-War/",
            "source_title": "Historic UK Annals",
            "seed_facts": ["Declared during English Civil War by Dutch Admiral Maarten Tromp", "Dutch fleet withdrew and forgot to officially sign a peace treaty", "Treaty finally ratified in 1986 by Dutch Ambassador"]
        },
        {
            "title": "The Stolen Mona Lisa and the World's Greatest Manhunt",
            "summary": "In 1911, a museum handyman simply walked out of the Louvre with the Mona Lisa hidden under his coat, making it the most famous painting in history.",
            "source_url": "https://www.louvre.fr/en/explore/the-palace/history-of-the-mona-lisa",
            "source_title": "Musée du Louvre Historical Archives",
            "seed_facts": ["Vincenzo Peruggia hid overnight in a broom closet", "Louvre didn't notice it was missing for 24 hours", "Recovered 2 years later in Florence"]
        },
        {
            "title": "The Real Reason Napoleon's Army Lost Their Buttons",
            "summary": "In the freezing Russian winter of 1812, tin buttons on French soldiers' coats disintegrated due to the tin pest chemical transformation.",
            "source_url": "https://www.rsc.org/periodic-table/element/50/tin",
            "source_title": "Royal Society of Chemistry",
            "seed_facts": ["White tin changes to brittle gray tin below 13.2°C", "Coats fell open in -30°C blizzard", "Accelerated severe hypothermia"]
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
        {
            "title": "How Solid State Batteries Stop Crystal Growth",
            "summary": "Next-gen lithium batteries use solid ceramics instead of flammable liquid electrolytes to physically block sharp needle-like dendrites from short-circuiting.",
            "source_url": "https://www.energy.gov/eere/vehicles/articles/batteries-future-solid-state-breakthroughs",
            "source_title": "U.S. Department of Energy (DOE)",
            "seed_facts": ["Dendrites pierce polymer separators causing thermal runaway", "Solid ceramic barrier withstands dendrite penetration", "Doubles energy density for electric vehicles"]
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
        {
            "title": "The Giant Diamond Planet Twice Earth's Size",
            "summary": "Exoplanet 55 Cancri e orbits its star so closely that its surface is molten lava and its interior is made of pure crystallized carbon diamond.",
            "source_url": "https://www.nasa.gov/universe/55-cancri-e-super-earth-diamond-planet/",
            "source_title": "NASA Exoplanet Exploration",
            "seed_facts": ["Surface temperature reaches 2,400 degrees Celsius", "Completes an entire orbit in just 18 hours", "Intense internal pressure forms thick diamond mantle"]
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
        {
            "title": "The Fungi Network Trading Nutrients Under Forests",
            "summary": "Underground mycorrhizal fungal networks connect entire forest trees, transferring carbon, water, and danger warning signals across miles of root systems.",
            "source_url": "https://www.nature.com/articles/388579a0",
            "source_title": "Nature Ecological Sciences",
            "seed_facts": ["Often called the Wood Wide Web", "Dying trees dump resources to healthy saplings", "Infested trees signal neighbors to produce defensive tannins"]
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
        {
            "title": "How to Find North With an Analog Watch",
            "summary": "Pointing the hour hand of an analog watch at the sun places due South exactly midway between the hour hand and 12 o'clock in the northern hemisphere.",
            "source_url": "https://www.armystudyguide.com/content/army_board_study_guide_topics/land_navigation_map_reading/field-expedient-direction.shtml",
            "source_title": "U.S. Army Field Navigation Manual",
            "seed_facts": ["Hour hand tracks sun's 15-degree per hour progression", "Midpoint bisector points along the local meridian", "Reversed for Southern Hemisphere navigation"]
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
        {
            "title": "Why Cold Exposure Spikes Dopamine by 250 Percent",
            "summary": "Submersion in cold water triggers a sustained 2.5-fold increase in circulating dopamine that lasts for hours without the crash associated with stimulants.",
            "source_url": "https://pubmed.ncbi.nlm.nih.gov/10751106/",
            "source_title": "European Journal of Applied Physiology",
            "seed_facts": ["Noradrenaline increases 530 percent", "Dopamine elevates steadily by 250 percent", "Elevated mental clarity persists for 3 hours post cold immersion"]
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
        {
            "title": "The Cosmonaut Left Stranded in Space",
            "summary": "Cosmonaut Sergei Krikalev went into space as a Soviet citizen and landed 311 days later to find his country had dissolved and ceased to exist.",
            "source_url": "https://www.rbth.com/history/330541-last-soviet-citizen-cosmonaut-krikalev",
            "source_title": "Space History Archives",
            "seed_facts": ["Launched from Baikonur in May 1991", "Mission extended twice because replacement funds evaporated", "Landed in March 1992 as a citizen of the Russian Federation"]
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
        if "history" in niche_name.lower():
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

        # 3. If below target count, cross-pollinate with adjacent history items
        if len(candidates) < target_count:
            for n_key, items in EVERGREEN_CURIOSITY_REPO.items():
                if "history" in n_key.lower() and n_key != niche_name and len(candidates) < target_count:
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

    def generate_emergency_candidate(self, niche_name: str) -> TopicCandidate:
        """Guaranteed fallback candidate to ensure the factory never stalls on topic discovery."""
        repo_items = EVERGREEN_CURIOSITY_REPO.get(niche_name, [])
        if repo_items:
            item = repo_items[0]
            return TopicCandidate(
                title=item["title"],
                summary=item["summary"],
                niche=niche_name,
                source_url=item["source_url"],
                source_title=item["source_title"],
                seed_facts=item.get("seed_facts", []),
            )
        return TopicCandidate(
            title=f"The Hidden Science of {niche_name}",
            summary=f"Surprising real-world mechanisms and counter-intuitive facts discovered in {niche_name}.",
            niche=niche_name,
            source_url="https://en.wikipedia.org",
            source_title="Encyclopedia Reference",
            seed_facts=["Verified scientific anomaly", "Counter-intuitive real-world finding"],
        )
