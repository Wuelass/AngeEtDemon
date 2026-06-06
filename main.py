from flask import Flask, jsonify, render_template
import requests
import urllib3
from functools import lru_cache
import re
import html

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

LOL_API = "https://127.0.0.1:2999/liveclientdata"

DDRAGON_LANGUAGE = "fr_FR"
DDRAGON_VERSIONS_URL = "https://ddragon.leagueoflegends.com/api/versions.json"
DDRAGON_ITEM_DATA_URL = "https://ddragon.leagueoflegends.com/cdn/{version}/data/{language}/item.json"
DDRAGON_CHAMPION_SUMMARY_URL = "https://ddragon.leagueoflegends.com/cdn/{version}/data/{language}/champion.json"
DDRAGON_CHAMPION_DETAIL_URL = "https://ddragon.leagueoflegends.com/cdn/{version}/data/{language}/champion/{champion_key}.json"
DDRAGON_RUNES_URL = "https://ddragon.leagueoflegends.com/cdn/{version}/data/{language}/runesReforged.json"


CHAMPION_ALIASES = {
    "wukong": "MonkeyKing",
    "monkeyking": "MonkeyKing",
    "nunu": "Nunu",
    "nunuandwillump": "Nunu",
    "nunuwillump": "Nunu",
    "ksante": "KSante",
    "kaisa": "Kaisa",
    "khazix": "Khazix",
    "chogath": "Chogath",
    "kogmaw": "KogMaw",
    "velkoz": "Velkoz",
    "reksai": "RekSai",
    "belveth": "Belveth",
    "drmundo": "DrMundo",
    "tahmkench": "TahmKench",
    "twistedfate": "TwistedFate",
    "leesin": "LeeSin",
    "masteryi": "MasterYi",
    "missfortune": "MissFortune",
    "jarvaniv": "JarvanIV",
    "xinzhao": "XinZhao",
    "renataglasc": "Renata",
}


BONUS_STAT_KEYS = [
    "hp",
    "mana",
    "ad",
    "ap",
    "armor",
    "magicResist",
    "attackSpeedPercent",
    "critChancePercent",
    "critDamagePercent",
    "moveSpeedFlat",
    "moveSpeedPercent",
    "hpRegenFlat",
    "hpRegenBasePercent",
    "manaRegenFlat",
    "manaRegenBasePercent",
    "lifeStealPercent",
    "abilityHaste",
    "armorPenFlat",
    "armorPenPercent",
    "magicPenFlat",
    "magicPenPercent",
    "healShieldPowerPercent",
]


ITEM_STAT_CONFIG = {
    "FlatHPPoolMod": ("hp", "PV", "flat"),
    "FlatMPPoolMod": ("mana", "Mana", "flat"),
    "FlatPhysicalDamageMod": ("ad", "AD", "flat"),
    "FlatMagicDamageMod": ("ap", "AP", "flat"),
    "FlatArmorMod": ("armor", "Armure", "flat"),
    "FlatSpellBlockMod": ("magicResist", "Résistance magique", "flat"),

    "PercentAttackSpeedMod": ("attackSpeedPercent", "Vitesse d'attaque", "percent"),
    "FlatCritChanceMod": ("critChancePercent", "Chance de coup critique", "percent"),
    "PercentCritChanceMod": ("critChancePercent", "Chance de coup critique", "percent"),
    "PercentCritDamageMod": ("critDamagePercent", "Dégâts critiques", "percent"),

    "FlatMovementSpeedMod": ("moveSpeedFlat", "Vitesse de déplacement", "flat"),
    "PercentMovementSpeedMod": ("moveSpeedPercent", "Vitesse de déplacement", "percent"),

    "FlatHPRegenMod": ("hpRegenFlat", "Régénération PV", "flat"),
    "PercentBaseHPRegenMod": ("hpRegenBasePercent", "Régénération PV de base", "percent"),
    "FlatMPRegenMod": ("manaRegenFlat", "Régénération mana", "flat"),
    "PercentBaseMPRegenMod": ("manaRegenBasePercent", "Régénération mana de base", "percent"),

    "PercentLifeStealMod": ("lifeStealPercent", "Vol de vie", "percent"),

    "FlatAbilityHasteMod": ("abilityHaste", "Hâte de compétence", "flat"),
    "AbilityHaste": ("abilityHaste", "Hâte de compétence", "flat"),

    "FlatArmorPenetrationMod": ("armorPenFlat", "Pénétration d'armure", "flat"),
    "PercentArmorPenetrationMod": ("armorPenPercent", "Pénétration d'armure", "percent"),
    "FlatMagicPenetrationMod": ("magicPenFlat", "Pénétration magique", "flat"),
    "PercentMagicPenetrationMod": ("magicPenPercent", "Pénétration magique", "percent"),

    "PercentHealAndShieldPowerMod": ("healShieldPowerPercent", "Puissance soins et boucliers", "percent"),
}


LIVE_STAT_CONFIG = {
    "abilityPower": ("AP", "number"),
    "attackDamage": ("AD", "number"),
    "armor": ("Armure", "number"),
    "magicResist": ("Résistance magique", "number"),
    "currentHealth": ("PV actuels", "number"),
    "maxHealth": ("PV max", "number"),
    "resourceValue": ("Ressource actuelle", "number"),
    "resourceMax": ("Ressource max", "number"),
    "moveSpeed": ("Vitesse de déplacement", "number"),
    "attackSpeed": ("Vitesse d'attaque", "number"),
    "attackRange": ("Portée d'attaque", "number"),
    "critChance": ("Chance critique", "percent"),
    "critDamage": ("Dégâts critiques", "percent"),
    "lifeSteal": ("Vol de vie", "percent"),
    "abilityHaste": ("Hâte de compétence", "number"),
    "armorPenetrationFlat": ("Pénétration armure flat", "number"),
    "armorPenetrationPercent": ("Pénétration armure", "percent"),
    "bonusArmorPenetrationPercent": ("Pénétration armure bonus", "percent"),
    "magicPenetrationFlat": ("Pénétration magique flat", "number"),
    "magicPenetrationPercent": ("Pénétration magique", "percent"),
    "bonusMagicPenetrationPercent": ("Pénétration magique bonus", "percent"),
    "healthRegenRate": ("Régénération PV", "number"),
    "tenacity": ("Ténacité", "percent"),
}


OBJECTIVE_LABELS = {
    "BaronKill": "Baron Nashor",
    "HeraldKill": "Héraut",
    "AtakhanKill": "Atakhan",
}


DRAGON_LABELS = {
    "air": "Dragon des nuages",
    "cloud": "Dragon des nuages",
    "earth": "Dragon montagne",
    "mountain": "Dragon montagne",
    "fire": "Dragon infernal",
    "infernal": "Dragon infernal",
    "hextech": "Dragon Hextech",
    "chemtech": "Dragon techno-chimique",
    "water": "Dragon océan",
    "ocean": "Dragon océan",
    "elder": "Dragon ancestral",
}


def safe_number(value, default=0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def clamp(value, min_value, max_value):
    return max(min_value, min(value, max_value))


def clean_html_text(raw_text):
    if not raw_text:
        return ""

    text = str(raw_text)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</li>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<li>", "- ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)

    return html.unescape(text).strip()


def normalize_text(value):
    if value is None:
        return ""

    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def normalize_player_name(value):
    if value is None:
        return ""

    name = str(value).split("#", 1)[0]
    return normalize_text(name)


def format_number(value, decimals=0):
    value = safe_number(value, 0)

    if abs(value - round(value)) < 0.05:
        return str(int(round(value)))

    return f"{value:.{decimals}f}".replace(".", ",")


def format_percent(decimal_value):
    return f"{format_number(safe_number(decimal_value) * 100, 1)}%"


def format_live_stat(value, kind):
    if kind == "percent":
        numeric_value = safe_number(value, 0)
        if abs(numeric_value) > 1:
            return f"{format_number(numeric_value, 1)}%"

        return format_percent(value)

    return format_number(value, 2)


def format_bonus_number(value):
    value = safe_number(value, 0)

    if abs(value) < 0.0001:
        return "—"

    sign = "+" if value > 0 else ""
    return f"{sign}{format_number(value, 1)}"


def format_bonus_percent(decimal_value):
    value = safe_number(decimal_value, 0)

    if abs(value) < 0.0001:
        return "—"

    sign = "+" if value > 0 else ""
    return f"{sign}{format_percent(value)}"


def format_attack_speed(value):
    return f"{safe_number(value, 0):.3f}".replace(".", ",")


def empty_bonus_stats():
    return {key: 0 for key in BONUS_STAT_KEYS}


def merge_bonus_stats(target, source, multiplier=1):
    for key in BONUS_STAT_KEYS:
        target[key] += safe_number(source.get(key), 0) * multiplier


@lru_cache(maxsize=1)
def get_ddragon_version():
    try:
        response = requests.get(DDRAGON_VERSIONS_URL, timeout=3)
        response.raise_for_status()
        versions = response.json()
        return versions[0]
    except Exception:
        return "15.1.1"


@lru_cache(maxsize=1)
def get_ddragon_items():
    version = get_ddragon_version()

    try:
        response = requests.get(
            DDRAGON_ITEM_DATA_URL.format(
                version=version,
                language=DDRAGON_LANGUAGE
            ),
            timeout=5
        )
        response.raise_for_status()
        data = response.json()
        return data.get("data", {})
    except Exception:
        return {}


@lru_cache(maxsize=1)
def get_ddragon_champion_summary():
    version = get_ddragon_version()

    try:
        response = requests.get(
            DDRAGON_CHAMPION_SUMMARY_URL.format(
                version=version,
                language=DDRAGON_LANGUAGE
            ),
            timeout=5
        )
        response.raise_for_status()
        data = response.json()
        return data.get("data", {})
    except Exception:
        return {}


@lru_cache(maxsize=1)
def get_ddragon_runes():
    version = get_ddragon_version()

    try:
        response = requests.get(
            DDRAGON_RUNES_URL.format(
                version=version,
                language=DDRAGON_LANGUAGE
            ),
            timeout=5
        )
        response.raise_for_status()
        return response.json()
    except Exception:
        return []


@lru_cache(maxsize=1)
def get_champion_lookup():
    champions = get_ddragon_champion_summary()
    lookup = {}

    for champion_key, champion_data in champions.items():
        possible_values = [
            champion_key,
            champion_data.get("id"),
            champion_data.get("key"),
            champion_data.get("name"),
        ]

        for value in possible_values:
            normalized = normalize_text(value)
            if normalized:
                lookup[normalized] = champion_key

    for alias, champion_key in CHAMPION_ALIASES.items():
        if champion_key in champions:
            lookup[alias] = champion_key

    return lookup


@lru_cache(maxsize=1)
def get_rune_lookup():
    rune_trees = get_ddragon_runes()
    lookup = {
        "runes": {},
        "trees": {}
    }

    for tree in rune_trees:
        tree_info = {
            "id": tree.get("id"),
            "key": tree.get("key"),
            "name": tree.get("name"),
            "iconUrl": get_rune_icon_url(tree.get("icon")),
        }

        for value in [tree.get("id"), tree.get("key"), tree.get("name")]:
            normalized = normalize_text(value)
            if normalized:
                lookup["trees"][normalized] = tree_info

        for slot_index, slot in enumerate(tree.get("slots", [])):
            for rune in slot.get("runes", []):
                rune_info = {
                    "id": rune.get("id"),
                    "key": rune.get("key"),
                    "name": rune.get("name"),
                    "shortDesc": clean_html_text(rune.get("shortDesc", "")),
                    "longDesc": clean_html_text(rune.get("longDesc", "")),
                    "iconUrl": get_rune_icon_url(rune.get("icon")),
                    "tree": tree_info,
                    "isKeystone": slot_index == 0,
                }

                for value in [rune.get("id"), rune.get("key"), rune.get("name")]:
                    normalized = normalize_text(value)
                    if normalized:
                        lookup["runes"][normalized] = rune_info

    return lookup


@lru_cache(maxsize=256)
def get_champion_detail(champion_key):
    if not champion_key:
        return None

    version = get_ddragon_version()

    try:
        response = requests.get(
            DDRAGON_CHAMPION_DETAIL_URL.format(
                version=version,
                language=DDRAGON_LANGUAGE,
                champion_key=champion_key
            ),
            timeout=5
        )
        response.raise_for_status()
        data = response.json()
        return data.get("data", {}).get(champion_key)
    except Exception:
        return None


def find_champion_key(player):
    lookup = get_champion_lookup()

    candidates = []

    raw_champion_name = player.get("rawChampionName")
    if raw_champion_name:
        candidates.append(raw_champion_name)
        candidates.append(str(raw_champion_name).replace("game_character_displayname_", ""))
        candidates.append(str(raw_champion_name).split("_")[-1])

    candidates.extend([
        player.get("championName"),
        player.get("championId"),
        player.get("championID"),
        player.get("championKey"),
    ])

    for candidate in candidates:
        normalized = normalize_text(candidate)
        if not normalized:
            continue

        if normalized in lookup:
            return lookup[normalized]

        if normalized in CHAMPION_ALIASES:
            return CHAMPION_ALIASES[normalized]

    return None


def get_item_icon_url(item_id):
    if not item_id:
        return None

    version = get_ddragon_version()
    return f"https://ddragon.leagueoflegends.com/cdn/{version}/img/item/{item_id}.png"


def get_rune_icon_url(icon_path):
    if not icon_path:
        return None

    return f"https://ddragon.leagueoflegends.com/cdn/img/{icon_path}"


def get_passive_icon_url(image_name):
    if not image_name:
        return None

    version = get_ddragon_version()
    return f"https://ddragon.leagueoflegends.com/cdn/{version}/img/passive/{image_name}"


def get_champion_icon_url(champion_key):
    if not champion_key:
        return None

    version = get_ddragon_version()
    return f"https://ddragon.leagueoflegends.com/cdn/{version}/img/champion/{champion_key}.png"


def get_item_data(item_id):
    if not item_id:
        return {}

    return get_ddragon_items().get(str(item_id), {})


def get_item_total_gold(item_id, fallback_price=0):
    item_data = get_item_data(item_id)

    if not item_data:
        return safe_number(fallback_price, 0)

    gold_data = item_data.get("gold", {})
    return safe_number(gold_data.get("total"), fallback_price)


def build_champion_passive(champion_detail):
    if not champion_detail:
        return {
            "available": False,
            "message": "Passif du champion indisponible : champion introuvable dans Data Dragon."
        }

    passive = champion_detail.get("passive") or {}
    image = passive.get("image") or {}

    if not passive:
        return {
            "available": False,
            "message": "Passif du champion indisponible dans Data Dragon."
        }

    return {
        "available": True,
        "name": passive.get("name", "Passif inconnu"),
        "description": clean_html_text(passive.get("description", "")),
        "iconUrl": get_passive_icon_url(image.get("full")),
    }


def format_item_stat_line(label, value, kind):
    value = safe_number(value, 0)

    if kind == "percent":
        return f"+{format_percent(value)} {label}"

    return f"+{format_number(value, 1)} {label}"


def parse_item_stats(raw_stats):
    bonus_stats = empty_bonus_stats()
    stat_lines = []

    for ddragon_stat_key, raw_value in raw_stats.items():
        value = safe_number(raw_value, 0)

        if abs(value) < 0.0001:
            continue

        config = ITEM_STAT_CONFIG.get(ddragon_stat_key)

        if not config:
            stat_lines.append(f"{ddragon_stat_key} : {format_number(value, 2)}")
            continue

        target_key, label, kind = config

        if target_key in bonus_stats:
            bonus_stats[target_key] += value

        stat_lines.append(format_item_stat_line(label, value, kind))

    return bonus_stats, stat_lines


def rune_from_live_payload(raw_rune, fallback_tree=None, is_keystone=False):
    rune_id = raw_rune.get("id") or raw_rune.get("runeId") or raw_rune.get("runeID")
    rune_key = raw_rune.get("key")
    lookup = get_rune_lookup()
    rune_info = None

    if normalize_text(rune_id) in lookup["trees"]:
        return None

    for value in [rune_id, rune_key, raw_rune.get("name"), raw_rune.get("displayName")]:
        normalized = normalize_text(value)
        if normalized and normalized in lookup["runes"]:
            rune_info = lookup["runes"][normalized]
            break

    if rune_info:
        return {
            **rune_info,
            "isKeystone": is_keystone or rune_info.get("isKeystone", False),
        }

    name = raw_rune.get("displayName") or raw_rune.get("name") or raw_rune.get("rawDisplayName")
    description = (
        raw_rune.get("description")
        or raw_rune.get("shortDesc")
        or raw_rune.get("longDesc")
        or raw_rune.get("rawDescription")
        or ""
    )

    cleaned_description = clean_html_text(description)

    if cleaned_description.startswith(("perkstyle_tooltip_", "perk_tooltip_")):
        return None

    if not name and not rune_id:
        return None

    return {
        "id": rune_id,
        "key": rune_key,
        "name": clean_html_text(name) or f"Rune {rune_id}",
        "shortDesc": cleaned_description,
        "longDesc": cleaned_description,
        "iconUrl": get_rune_icon_url(raw_rune.get("icon")),
        "tree": fallback_tree,
        "isKeystone": is_keystone,
    }


def tree_from_live_payload(raw_tree):
    if not raw_tree:
        return None

    lookup = get_rune_lookup()

    if isinstance(raw_tree, dict):
        candidates = [
            raw_tree.get("id"),
            raw_tree.get("key"),
            raw_tree.get("name"),
            raw_tree.get("displayName"),
        ]
    else:
        candidates = [raw_tree]

    for value in candidates:
        normalized = normalize_text(value)
        if normalized and normalized in lookup["trees"]:
            return lookup["trees"][normalized]

    if isinstance(raw_tree, dict):
        name = raw_tree.get("displayName") or raw_tree.get("name") or raw_tree.get("key")
        if name:
            return {
                "id": raw_tree.get("id"),
                "key": raw_tree.get("key"),
                "name": clean_html_text(name),
                "iconUrl": get_rune_icon_url(raw_tree.get("icon")),
            }

    return None


def collect_rune_payloads(value, collected=None):
    if collected is None:
        collected = []

    if isinstance(value, dict):
        looks_like_rune = any(key in value for key in [
            "runeId",
            "runeID",
            "shortDesc",
            "longDesc",
            "rawDescription",
        ]) or (
            any(key in value for key in ["displayName", "rawDisplayName"])
            and any(key in value for key in ["description", "rawDescription", "shortDesc", "longDesc"])
        )

        if looks_like_rune:
            collected.append(value)

        for child in value.values():
            collect_rune_payloads(child, collected)

    elif isinstance(value, list):
        for child in value:
            collect_rune_payloads(child, collected)

    return collected


def collect_known_rune_ids(value, collected=None):
    if collected is None:
        collected = []

    lookup = get_rune_lookup()

    if isinstance(value, dict):
        for child in value.values():
            collect_known_rune_ids(child, collected)

    elif isinstance(value, list):
        for child in value:
            collect_known_rune_ids(child, collected)

    else:
        normalized = normalize_text(value)
        if normalized and normalized in lookup["runes"]:
            collected.append(value)

    return collected


def build_runes_info(player, active_player, is_active_player):
    sources = [
        player.get("fullRunes"),
        player.get("runes"),
    ]

    if is_active_player:
        sources.insert(0, active_player.get("fullRunes"))
        sources.insert(1, active_player.get("runes"))

    source = next((item for item in sources if item), None)

    if not source:
        return {
            "available": False,
            "message": "Runes indisponibles via l'API locale.",
            "runes": [],
        }

    primary_tree = None
    secondary_tree = None

    if isinstance(source, dict):
        primary_tree = tree_from_live_payload(
            source.get("primaryRuneTree")
            or source.get("primaryStyle")
            or source.get("primary")
        )
        secondary_tree = tree_from_live_payload(
            source.get("secondaryRuneTree")
            or source.get("secondaryStyle")
            or source.get("secondary")
        )

    raw_runes = collect_rune_payloads(source)
    runes = []
    seen = set()

    for raw_rune in raw_runes:
        rune = rune_from_live_payload(raw_rune, primary_tree)
        if not rune:
            continue

        rune_id = normalize_text(rune.get("id") or rune.get("key") or rune.get("name"))
        if rune_id in seen:
            continue

        seen.add(rune_id)
        runes.append(rune)

        rune_tree = rune.get("tree")
        if rune.get("isKeystone") and rune_tree and not primary_tree:
            primary_tree = rune_tree
        elif rune_tree and primary_tree and rune_tree.get("id") != primary_tree.get("id") and not secondary_tree:
            secondary_tree = rune_tree

    if not runes:
        lookup = get_rune_lookup()
        for rune_id in collect_known_rune_ids(source):
            rune = lookup["runes"].get(normalize_text(rune_id))
            if not rune:
                continue

            normalized = normalize_text(rune.get("id") or rune.get("key") or rune.get("name"))
            if normalized in seen:
                continue

            seen.add(normalized)
            runes.append(rune)

            rune_tree = rune.get("tree")
            if rune.get("isKeystone") and rune_tree and not primary_tree:
                primary_tree = rune_tree
            elif rune_tree and primary_tree and rune_tree.get("id") != primary_tree.get("id") and not secondary_tree:
                secondary_tree = rune_tree

    if not runes:
        return {
            "available": False,
            "message": "Runes indisponibles via l'API locale.",
            "runes": [],
        }

    keystone = next((rune for rune in runes if rune.get("isKeystone")), runes[0])

    return {
        "available": True,
        "message": "",
        "primaryTree": primary_tree,
        "secondaryTree": secondary_tree,
        "keystone": keystone,
        "runes": runes,
    }


def build_live_stats(active_player, is_active_player):
    if not is_active_player:
        return {
            "available": False,
            "exact": False,
            "message": "Stats live exactes indisponibles pour ce joueur. Affichage estimé avec niveau + items + données statiques.",
            "rows": [],
            "byKey": {},
        }

    champion_stats = active_player.get("championStats") or {}

    if not champion_stats:
        return {
            "available": False,
            "exact": False,
            "message": "Stats live exactes indisponibles pour ce joueur.",
            "rows": [],
            "byKey": {},
        }

    rows = []
    by_key = {}

    for key, (label, kind) in LIVE_STAT_CONFIG.items():
        if key in champion_stats:
            value_text = format_live_stat(champion_stats.get(key), kind)
            rows.append({
                "key": key,
                "label": label,
                "valueText": value_text,
            })
            by_key[key] = value_text

    return {
        "available": bool(rows),
        "exact": bool(rows),
        "message": "Stats live exactes depuis activePlayer.championStats." if rows else "Aucune stat live exacte exploitable dans championStats.",
        "rows": rows,
        "byKey": by_key,
    }


def lol_get(endpoint):
    url = f"{LOL_API}/{endpoint}"

    response = requests.get(
        url,
        verify=False,
        timeout=2
    )

    response.raise_for_status()
    return response.json()


def get_live_data():
    try:
        try:
            all_game_data = lol_get("allgamedata") or {}
            return {
                "players": all_game_data.get("allPlayers") or [],
                "activePlayer": all_game_data.get("activePlayer") or {},
                "events": (all_game_data.get("events") or {}).get("Events") or [],
                "gameTime": safe_number((all_game_data.get("gameData") or {}).get("gameTime"), 0),
                "source": "allgamedata",
            }, None

        except Exception:
            players = lol_get("playerlist")

            try:
                active_player = lol_get("activeplayer")
            except Exception:
                active_player = None

            return {
                "players": players,
                "activePlayer": active_player or {},
                "events": [],
                "gameTime": 0,
                "source": "fallback",
            }, None

    except requests.exceptions.ConnectionError:
        return None, "Impossible de se connecter au client LoL. Lance une game puis réessaie."

    except requests.exceptions.Timeout:
        return None, "Le client LoL ne répond pas assez vite."

    except requests.exceptions.HTTPError as e:
        return None, f"Erreur HTTP depuis le client LoL : {e}"

    except Exception as e:
        return None, f"Erreur inconnue : {e}"


def player_identity_values(player):
    return [
        player.get("riotId"),
        player.get("summonerName"),
        player.get("championName"),
        player.get("rawChampionName"),
    ]


def find_player_team_by_name(name, players):
    normalized_name = normalize_player_name(name)

    if not normalized_name:
        return None

    for player in players:
        for candidate in player_identity_values(player):
            normalized_candidate = normalize_player_name(candidate)
            if normalized_candidate and normalized_candidate == normalized_name:
                return player.get("team")

    for player in players:
        for candidate in player_identity_values(player):
            normalized_candidate = normalize_player_name(candidate)
            if normalized_candidate and (
                normalized_candidate in normalized_name
                or normalized_name in normalized_candidate
            ):
                return player.get("team")

    return None


def dragon_label(event):
    dragon_type = (
        event.get("DragonType")
        or event.get("DragonName")
        or event.get("MonsterType")
        or event.get("ObjectiveName")
        or ""
    )
    normalized = normalize_text(dragon_type)

    for key, label in DRAGON_LABELS.items():
        if key in normalized:
            return label

    return "Dragon élémentaire"


def timed_buff_state(event_time, game_time, duration):
    remaining = int(round(duration - max(0, game_time - event_time)))

    if remaining > 0:
        return f"Buff actif encore {remaining}s"

    return "Buff expiré"


def build_team_objectives(players, events, game_time):
    objectives = {
        "ORDER": {
            "effects": [],
            "dragonCounts": {},
            "heraldKills": 0,
            "atakhanKills": 0,
        },
        "CHAOS": {
            "effects": [],
            "dragonCounts": {},
            "heraldKills": 0,
            "atakhanKills": 0,
        },
    }

    for event in events or []:
        event_name = event.get("EventName")
        if event_name not in ["DragonKill", "BaronKill", "HeraldKill", "AtakhanKill"]:
            continue

        team = find_player_team_by_name(event.get("KillerName"), players)
        if team not in objectives:
            continue

        event_time = safe_number(event.get("EventTime"), 0)
        team_objectives = objectives[team]

        if event_name == "DragonKill":
            label = dragon_label(event)
            team_objectives["dragonCounts"][label] = team_objectives["dragonCounts"].get(label, 0) + 1

            if "ancestral" in normalize_text(label):
                team_objectives["effects"].append({
                    "label": label,
                    "detail": timed_buff_state(event_time, game_time, 150),
                })

        elif event_name == "BaronKill":
            team_objectives["effects"].append({
                "label": OBJECTIVE_LABELS[event_name],
                "detail": timed_buff_state(event_time, game_time, 180),
            })

        elif event_name == "HeraldKill":
            team_objectives["heraldKills"] += 1

        elif event_name == "AtakhanKill":
            team_objectives["atakhanKills"] += 1

    for team_objectives in objectives.values():
        for dragon_name, count in sorted(team_objectives["dragonCounts"].items()):
            if "ancestral" not in normalize_text(dragon_name):
                team_objectives["effects"].append({
                    "label": "Dragons élémentaires",
                    "detail": f"{dragon_name} x{count}",
                })

        if team_objectives["heraldKills"]:
            team_objectives["effects"].append({
                "label": "Héraut",
                "detail": f"{team_objectives['heraldKills']} héraut tué",
            })

        if team_objectives["atakhanKills"]:
            team_objectives["effects"].append({
                "label": "Atakhan",
                "detail": f"{team_objectives['atakhanKills']} Atakhan tué",
            })

        team_objectives["message"] = (
            "" if team_objectives["effects"]
            else "Aucun objectif ou buff d'équipe détecté."
        )

    return objectives


def same_riot_id(a, b):
    if not a or not b:
        return False

    return normalize_player_name(a) == normalize_player_name(b)


def level_growth_multiplier(level):
    level = clamp(safe_int(level, 1), 1, 18)

    if level <= 1:
        return 0

    level_minus_one = level - 1
    return (0.7025 + 0.0175 * level_minus_one) * level_minus_one


def stat_with_growth(stats, base_key, per_level_key, level):
    base = safe_number(stats.get(base_key), 0)
    per_level = safe_number(stats.get(per_level_key), 0)
    growth = level_growth_multiplier(level)
    return base + per_level * growth


def build_stat_row(label, base_text, bonus_text, total_text, live_keys=None):
    return {
        "label": label,
        "baseText": base_text,
        "bonusText": bonus_text,
        "totalText": total_text,
        "liveKeys": live_keys or []
    }


def calculate_champion_stats(champion_detail, level, item_bonus):
    level = clamp(safe_int(level, 1), 1, 18)

    if not champion_detail:
        return {
            "found": False,
            "level": level,
            "statRows": [],
            "note": "Champion introuvable dans Data Dragon."
        }

    stats = champion_detail.get("stats", {})

    base_hp = stat_with_growth(stats, "hp", "hpperlevel", level)
    base_mana = stat_with_growth(stats, "mp", "mpperlevel", level)
    base_ad = stat_with_growth(stats, "attackdamage", "attackdamageperlevel", level)
    base_armor = stat_with_growth(stats, "armor", "armorperlevel", level)
    base_magic_resist = stat_with_growth(stats, "spellblock", "spellblockperlevel", level)
    base_hp_regen = stat_with_growth(stats, "hpregen", "hpregenperlevel", level)
    base_mana_regen = stat_with_growth(stats, "mpregen", "mpregenperlevel", level)
    base_crit = stat_with_growth(stats, "crit", "critperlevel", level) / 100

    base_attack_speed_raw = safe_number(stats.get("attackspeed"), 0)
    attack_speed_level_percent = safe_number(stats.get("attackspeedperlevel"), 0) / 100 * level_growth_multiplier(level)
    base_attack_speed = base_attack_speed_raw * (1 + attack_speed_level_percent)

    base_move_speed = safe_number(stats.get("movespeed"), 0)
    attack_range = safe_number(stats.get("attackrange"), 0)

    total_hp = base_hp + item_bonus["hp"]
    total_mana = base_mana + item_bonus["mana"]
    total_ad = base_ad + item_bonus["ad"]
    total_ap = item_bonus["ap"]
    total_armor = base_armor + item_bonus["armor"]
    total_magic_resist = base_magic_resist + item_bonus["magicResist"]

    total_attack_speed = base_attack_speed_raw * (
        1 + attack_speed_level_percent + item_bonus["attackSpeedPercent"]
    )

    total_crit = base_crit + item_bonus["critChancePercent"]

    total_move_speed = (
        base_move_speed + item_bonus["moveSpeedFlat"]
    ) * (1 + item_bonus["moveSpeedPercent"])

    total_hp_regen = (
        base_hp_regen * (1 + item_bonus["hpRegenBasePercent"])
    ) + item_bonus["hpRegenFlat"]

    total_mana_regen = (
        base_mana_regen * (1 + item_bonus["manaRegenBasePercent"])
    ) + item_bonus["manaRegenFlat"]

    stat_rows = [
        build_stat_row(
            "PV",
            format_number(base_hp, 1),
            format_bonus_number(item_bonus["hp"]),
            format_number(total_hp, 1),
            ["currentHealth", "maxHealth"]
        ),
        build_stat_row(
            "Mana",
            format_number(base_mana, 1),
            format_bonus_number(item_bonus["mana"]),
            format_number(total_mana, 1),
            ["resourceValue", "resourceMax"]
        ),
        build_stat_row(
            "AD",
            format_number(base_ad, 1),
            format_bonus_number(item_bonus["ad"]),
            format_number(total_ad, 1),
            ["attackDamage"]
        ),
        build_stat_row(
            "AP",
            "0",
            format_bonus_number(item_bonus["ap"]),
            format_number(total_ap, 1),
            ["abilityPower"]
        ),
        build_stat_row(
            "Armure",
            format_number(base_armor, 1),
            format_bonus_number(item_bonus["armor"]),
            format_number(total_armor, 1),
            ["armor"]
        ),
        build_stat_row(
            "Résistance magique",
            format_number(base_magic_resist, 1),
            format_bonus_number(item_bonus["magicResist"]),
            format_number(total_magic_resist, 1),
            ["magicResist"]
        ),
        build_stat_row(
            "Vitesse d'attaque",
            format_attack_speed(base_attack_speed),
            format_bonus_percent(item_bonus["attackSpeedPercent"]),
            format_attack_speed(total_attack_speed),
            ["attackSpeed"]
        ),
        build_stat_row(
            "Vitesse de déplacement",
            format_number(base_move_speed, 1),
            f"{format_bonus_number(item_bonus['moveSpeedFlat'])} / {format_bonus_percent(item_bonus['moveSpeedPercent'])}",
            format_number(total_move_speed, 1),
            ["moveSpeed"]
        ),
        build_stat_row(
            "Chance critique",
            format_percent(base_crit),
            format_bonus_percent(item_bonus["critChancePercent"]),
            format_percent(total_crit),
            ["critChance"]
        ),
        build_stat_row(
            "Dégâts critiques bonus",
            "0%",
            format_bonus_percent(item_bonus["critDamagePercent"]),
            format_percent(item_bonus["critDamagePercent"]),
            ["critDamage"]
        ),
        build_stat_row(
            "Portée d'attaque",
            format_number(attack_range, 1),
            "—",
            format_number(attack_range, 1),
            ["attackRange"]
        ),
        build_stat_row(
            "Régénération PV",
            format_number(base_hp_regen, 1),
            f"{format_bonus_number(item_bonus['hpRegenFlat'])} / {format_bonus_percent(item_bonus['hpRegenBasePercent'])}",
            format_number(total_hp_regen, 1),
            ["healthRegenRate"]
        ),
        build_stat_row(
            "Régénération mana",
            format_number(base_mana_regen, 1),
            f"{format_bonus_number(item_bonus['manaRegenFlat'])} / {format_bonus_percent(item_bonus['manaRegenBasePercent'])}",
            format_number(total_mana_regen, 1),
            []
        ),
        build_stat_row(
            "Vol de vie",
            "0%",
            format_bonus_percent(item_bonus["lifeStealPercent"]),
            format_percent(item_bonus["lifeStealPercent"]),
            ["lifeSteal"]
        ),
        build_stat_row(
            "Hâte de compétence",
            "0",
            format_bonus_number(item_bonus["abilityHaste"]),
            format_number(item_bonus["abilityHaste"], 1),
            ["abilityHaste"]
        ),
        build_stat_row(
            "Pénétration d'armure",
            "0",
            f"{format_bonus_number(item_bonus['armorPenFlat'])} / {format_bonus_percent(item_bonus['armorPenPercent'])}",
            f"{format_number(item_bonus['armorPenFlat'], 1)} / {format_percent(item_bonus['armorPenPercent'])}",
            ["armorPenetrationFlat", "armorPenetrationPercent"]
        ),
        build_stat_row(
            "Pénétration magique",
            "0",
            f"{format_bonus_number(item_bonus['magicPenFlat'])} / {format_bonus_percent(item_bonus['magicPenPercent'])}",
            f"{format_number(item_bonus['magicPenFlat'], 1)} / {format_percent(item_bonus['magicPenPercent'])}",
            ["magicPenetrationFlat", "magicPenetrationPercent"]
        ),
        build_stat_row(
            "Puissance soins/boucliers",
            "0%",
            format_bonus_percent(item_bonus["healShieldPowerPercent"]),
            format_percent(item_bonus["healShieldPowerPercent"]),
            []
        ),
    ]


    return {
        "found": True,
        "level": level,
        "statRows": stat_rows,
        "note": "Calcul = stats champion au niveau actuel + stats structurées des items Data Dragon. Les effets conditionnels restent présentés en texte quand ils ne sont pas fiables à convertir en chiffres."
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/players")
def api_players():
    live_data, error = get_live_data()

    if error:
        return jsonify({
            "ok": False,
            "error": error,
            "players": [],
            "teams": {}
        })

    players = live_data["players"]
    active_player = live_data.get("activePlayer") or {}

    active_riot_id = active_player.get("riotId")
    active_summoner_name = active_player.get("summonerName")
    active_current_gold = safe_number(active_player.get("currentGold"), 0)
    team_objectives = build_team_objectives(
        players=players,
        events=live_data.get("events") or [],
        game_time=live_data.get("gameTime") or 0
    )

    result = []

    team_gold = {
        "ORDER": 0,
        "CHAOS": 0
    }

    for player in players:
        riot_id = player.get("riotId") or player.get("summonerName", "Joueur inconnu")
        team = player.get("team", "UNKNOWN")
        level = clamp(safe_int(player.get("level"), 1), 1, 18)

        champion_key = find_champion_key(player)
        champion_detail = get_champion_detail(champion_key) if champion_key else None

        item_bonus_total = empty_bonus_stats()
        items = []
        item_gold = 0

        for item in player.get("items", []):
            item_id = item.get("itemID")
            item_data = get_item_data(item_id)

            live_price = safe_number(item.get("price"), 0)
            ddragon_total_price = get_item_total_gold(item_id, live_price)

            item_count = safe_number(item.get("count"), 1)
            if item_count < 1:
                item_count = 1

            item_stats_raw = item_data.get("stats", {})
            item_bonus, stat_lines = parse_item_stats(item_stats_raw)
            merge_bonus_stats(item_bonus_total, item_bonus, item_count)

            total_item_price = ddragon_total_price * item_count
            item_gold += total_item_price

            items.append({
                "name": item_data.get("name") or item.get("displayName", "Item inconnu"),
                "id": item_id,
                "slot": item.get("slot"),
                "count": int(item_count),
                "price": int(ddragon_total_price),
                "totalPrice": int(total_item_price),
                "livePrice": int(live_price),
                "iconUrl": get_item_icon_url(item_id),
                "description": clean_html_text(item_data.get("description", "")),
                "plaintext": clean_html_text(item_data.get("plaintext", "")),
                "statLines": stat_lines,
                "rawStats": item_stats_raw
            })

        champion_stats = calculate_champion_stats(
            champion_detail=champion_detail,
            level=level,
            item_bonus=item_bonus_total
        )

        is_active_player = (
            same_riot_id(riot_id, active_riot_id)
            or same_riot_id(riot_id, active_summoner_name)
            or same_riot_id(player.get("summonerName"), active_summoner_name)
            or same_riot_id(player.get("summonerName"), active_riot_id)
        )

        unspent_gold = active_current_gold if is_active_player else None

        displayed_gold = item_gold
        gold_is_exact = False

        if is_active_player:
            displayed_gold = item_gold + active_current_gold
            gold_is_exact = True

        if team in team_gold:
            team_gold[team] += displayed_gold

        champion_name = player.get("championName", "Champion inconnu")
        champion_title = ""

        if champion_detail:
            champion_name = champion_detail.get("name", champion_name)
            champion_title = champion_detail.get("title", "")

        result.append({
            "riotId": riot_id,
            "champion": champion_name,
            "team": team,
            "level": level,
            "position": player.get("position", ""),
            "isDead": player.get("isDead", False),
            "items": items,

            "championInfo": {
                "key": champion_key,
                "name": champion_name,
                "title": champion_title,
                "iconUrl": get_champion_icon_url(champion_key),
                "found": champion_detail is not None
            },

            "championStats": champion_stats,
            "liveStats": build_live_stats(active_player, is_active_player),
            "runes": build_runes_info(player, active_player, is_active_player),
            "teamObjectives": team_objectives.get(team, {
                "effects": [],
                "message": "Aucun objectif ou buff d'équipe détecté."
            }),
            "passive": build_champion_passive(champion_detail),
            "effectsNote": "Les effets conditionnels et non structurés sont affichés depuis les descriptions Data Dragon. Ils ne sont pas toujours convertibles en statistiques numériques fiables.",

            "gold": {
                "itemGold": int(item_gold),
                "unspentGold": int(unspent_gold) if unspent_gold is not None else None,
                "displayedGold": int(displayed_gold),
                "isExact": gold_is_exact
            }
        })

    return jsonify({
        "ok": True,
        "players": result,
        "teams": {
            "ORDER": {
                "gold": int(team_gold["ORDER"])
            },
            "CHAOS": {
                "gold": int(team_gold["CHAOS"])
            }
        }
    })


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
