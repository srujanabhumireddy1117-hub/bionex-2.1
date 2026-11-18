import random
from typing import Dict, Any, List, Optional


PRESET_VISION_ITEMS = {
    "needle_syringe": {
        "id": "preset_01",
        "name": "Used 24G Syringe with Needle",
        "detected_class": "Puncture Sharps / Needle",
        "confidence": 0.96,
        "is_mixed": False,
        "is_leaking": False,
        "category": "White",
        "receptacle": "White Translucent Sharps Container (Puncture-Proof)",
        "bounding_box": {"x": 28, "y": 35, "width": 44, "height": 30},
        "safety_notes": "Single intact sharp. Robotic gripper authorized for puncture-resistant deposit."
    },
    "iv_tubing": {
        "id": "preset_02",
        "name": "Contaminated IV Tubing & Saline Bag",
        "detected_class": "Contaminated Recyclable Plastics",
        "confidence": 0.94,
        "is_mixed": False,
        "is_leaking": False,
        "category": "Red",
        "receptacle": "Red Autoclavable Plastic Bin",
        "bounding_box": {"x": 20, "y": 25, "width": 60, "height": 50},
        "safety_notes": "Polyvinyl chloride tubing verified without needle. Autoclavable recycling eligible."
    },
    "soiled_gauze": {
        "id": "preset_03",
        "name": "Surgical Gauze Soiled with Blood",
        "detected_class": "Soiled Anatomical / Swabs",
        "confidence": 0.92,
        "is_mixed": False,
        "is_leaking": False,
        "category": "Yellow",
        "receptacle": "Yellow Biohazard Container (Incineration 1050°C)",
        "bounding_box": {"x": 35, "y": 30, "width": 30, "height": 40},
        "safety_notes": "Bio-fluid contaminated material. Enclosed drop to yellow chamber."
    },
    "glass_ampoule": {
        "id": "preset_04",
        "name": "Broken Antibiotic Glass Ampoule",
        "detected_class": "Contaminated Glassware / Ampoules",
        "confidence": 0.95,
        "is_mixed": False,
        "is_leaking": False,
        "category": "Blue",
        "receptacle": "Blue Puncture-Resistant Box (1% Hypochlorite Disinfection)",
        "bounding_box": {"x": 40, "y": 38, "width": 20, "height": 24},
        "safety_notes": "Non-cytotoxic medicine glass. Authorized for Blue chute."
    },
    "mixed_entangled": {
        "id": "preset_05",
        "name": "Needle Entangled with IV Tubing & Chemical Residue",
        "detected_class": "Mixed Entangled Hazard (Needle + Tubing)",
        "confidence": 0.68,
        "is_mixed": True,
        "is_leaking": True,
        "category": "Human Review",
        "receptacle": "HOLD IN TRAY (Human Staff Intervention)",
        "bounding_box": {"x": 22, "y": 20, "width": 56, "height": 60},
        "safety_notes": "CRITICAL: Multiple waste categories mechanically entangled. Force separation forbidden."
    },
    "unidentified_residue": {
        "id": "preset_06",
        "name": "Unlabeled Leaking Chemical Container",
        "detected_class": "Unidentified Chemical Specimen",
        "confidence": 0.52,
        "is_mixed": True,
        "is_leaking": True,
        "category": "Human Review",
        "receptacle": "HOLD IN TRAY (Human Staff Intervention)",
        "bounding_box": {"x": 30, "y": 25, "width": 40, "height": 50},
        "safety_notes": "Vision model confidence below 85% safety boundary. Chemical risk unverified."
    }
}


def simulate_waste_detection(item_text: str = "", preset_id: Optional[str] = None) -> Dict[str, Any]:
    if preset_id and preset_id in PRESET_VISION_ITEMS:
        return PRESET_VISION_ITEMS[preset_id]

    text = item_text.lower().strip()

    if any(w in text for w in ["mixed", "entangled", "tangled", "leaking", "unknown", "unlabeled", "unidentified", "suspicious", "chemical leak"]):
        return {
            "id": "custom_unsafe",
            "name": item_text,
            "detected_class": "Unsafe / Mixed / Unidentified Waste",
            "confidence": round(random.uniform(0.48, 0.72), 2),
            "is_mixed": True,
            "is_leaking": True,
            "category": "Human Review",
            "receptacle": "HOLD IN ENCLOSED TRAY (Nurse / Admin Review Required)",
            "bounding_box": {"x": 25, "y": 25, "width": 50, "height": 50},
            "safety_notes": "BioNex Interlock Triggered: Mechanical handling halted. Trained staff must intervene."
        }

    if any(w in text for w in ["needle", "syringe", "scalpel", "blade", "lancet", "trocar", "sharp"]):
        if any(w in text for w in ["tubing", "bottle", "vial", "bag"]) and "with" in text:
            return {
                "id": "custom_mixed_sharp",
                "name": item_text,
                "detected_class": "Mixed Sharp + Plastic Waste",
                "confidence": 0.74,
                "is_mixed": True,
                "is_leaking": False,
                "category": "Human Review",
                "receptacle": "HOLD IN TRAY (Human Review Required)",
                "bounding_box": {"x": 20, "y": 20, "width": 60, "height": 60},
                "safety_notes": "Sharp entangled with recyclable plastic. Manual separation prohibited."
            }
        return {
            "id": "custom_white",
            "name": item_text,
            "detected_class": "Puncture Sharps / Needle",
            "confidence": round(random.uniform(0.92, 0.98), 2),
            "is_mixed": False,
            "is_leaking": False,
            "category": "White",
            "receptacle": "White Translucent Sharps Container (Puncture-Proof)",
            "bounding_box": {"x": 30, "y": 32, "width": 40, "height": 36},
            "safety_notes": "Verified puncture-proof sharp item. PCA9685 arm routing enabled."
        }

    if any(w in text for w in ["iv tube", "tubing", "catheter", "urine bag", "glove", "dialysis", "cannula", "vacutainer"]):
        return {
            "id": "custom_red",
            "name": item_text,
            "detected_class": "Contaminated Recyclable Plastics",
            "confidence": round(random.uniform(0.90, 0.97), 2),
            "is_mixed": False,
            "is_leaking": False,
            "category": "Red",
            "receptacle": "Red Autoclavable Plastic Bin",
            "bounding_box": {"x": 25, "y": 25, "width": 50, "height": 50},
            "safety_notes": "Clean contaminated plastic identified. Routed to Red gate."
        }

    if any(w in text for w in ["gauze", "cotton", "bandage", "dressing", "anatomical", "tissue", "blood", "swab", "plaster"]):
        return {
            "id": "custom_yellow",
            "name": item_text,
            "detected_class": "Soiled Anatomical / Infectious Swab",
            "confidence": round(random.uniform(0.88, 0.96), 2),
            "is_mixed": False,
            "is_leaking": False,
            "category": "Yellow",
            "receptacle": "Yellow Biohazard Container (Incineration 1050°C)",
            "bounding_box": {"x": 32, "y": 30, "width": 36, "height": 40},
            "safety_notes": "Blood/infectious soiled item verified. Scheduled for Yellow incineration bin."
        }

    if any(w in text for w in ["vial", "ampoule", "broken glass", "glass bottle", "slide", "implant", "screw", "orthopedic"]):
        return {
            "id": "custom_blue",
            "name": item_text,
            "detected_class": "Medicine Glassware / Metallic Implant",
            "confidence": round(random.uniform(0.91, 0.98), 2),
            "is_mixed": False,
            "is_leaking": False,
            "category": "Blue",
            "receptacle": "Blue Puncture-Resistant Box (Disinfection & Recycling)",
            "bounding_box": {"x": 38, "y": 35, "width": 24, "height": 30},
            "safety_notes": "Glassware/metallic implant confirmed. Dispatched to Blue gate."
        }

    return {
        "id": "custom_uncertain",
        "name": item_text if item_text else "Unidentified Object",
        "detected_class": "Unidentified Object",
        "confidence": 0.62,
        "is_mixed": True,
        "is_leaking": False,
        "category": "Human Review",
        "receptacle": "HOLD IN ENCLOSED TRAY (Verification Needed)",
        "bounding_box": {"x": 30, "y": 30, "width": 40, "height": 40},
        "safety_notes": "Confidence < 85%. Automated segregation inhibited under BioNex safety rules."
    }
