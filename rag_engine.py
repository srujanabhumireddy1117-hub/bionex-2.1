import math
import os
import re
import json
from typing import List, Dict, Any, Optional, Tuple


class DocumentChunk:
    def __init__(self, doc_id: str, doc_name: str, section: str, page: int, chunk_id: int, content: str):
        self.doc_id = doc_id
        self.doc_name = doc_name
        self.section = section
        self.page = page
        self.chunk_id = chunk_id
        self.content = content
        self.terms: Dict[str, float] = {}

    def to_dict(self) -> dict:
        return {
            "doc_id": self.doc_id,
            "doc_name": self.doc_name,
            "section": self.section,
            "page": self.page,
            "chunk_id": self.chunk_id,
            "content": self.content,
        }


class BiomedicalRAGEngine:
    """
    RAG engine for BioNex Biomedical Waste System.
    Provides document chunking, vector space indexing (TF-IDF & Cosine Similarity),
    strict grounding, citation extraction, and safety guardrails.
    """
    def __init__(self):
        self.chunks: List[DocumentChunk] = []
        self.vocabulary: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
        self.initialized = False
        self._load_knowledge_base()

    def tokenize(self, text: str) -> List[str]:
        cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
        tokens = [t for t in cleaned.split() if len(t) > 2]
        return tokens

    def _split_into_chunks(self, text: str, doc_name: str, section: str = "General", page_start: int = 1, chunk_size: int = 350, overlap: int = 50) -> List[DocumentChunk]:
        words = text.split()
        chunks = []
        chunk_idx = 1
        i = 0
        current_page = page_start
        
        while i < len(words):
            chunk_words = words[i : i + chunk_size]
            chunk_text = " ".join(chunk_words)
            current_page = page_start + (i // 250)
            
            chunk = DocumentChunk(
                doc_id=doc_name.lower().replace(" ", "_"),
                doc_name=doc_name,
                section=section,
                page=current_page,
                chunk_id=chunk_idx,
                content=chunk_text.strip()
            )
            chunks.append(chunk)
            chunk_idx += 1
            i += (chunk_size - overlap)
            
        return chunks

    def _load_knowledge_base(self):
        """Loads official biomedical waste standards & hospital SOPs."""
        self.chunks.clear()

        cpcb_text = """
        GOVERNMENT OF INDIA - MINISTRY OF ENVIRONMENT, FOREST AND CLIMATE CHANGE
        BIO-MEDICAL WASTE MANAGEMENT RULES, 2016 (AMENDED 2018/2019)
        
        SECTION 1: DEFINITION AND APPLICABILITY
        Biomedical waste means any waste which is generated during the diagnosis, treatment or immunisation of human beings or animals or in research activities pertaining thereto or in the production or testing of biologicals.
        It is mandatory for all healthcare facilities (HCFs) to segregate biomedical waste at the point of generation according to the four prescribed color categories.

        SECTION 2: FOUR COLOUR-CODED CATEGORIES (SCHEDULE I)
        1. YELLOW CATEGORY:
        - Applicable Waste Items: Human anatomical waste, animal anatomical waste, soiled waste (items contaminated with blood, body fluids like dressings, plaster casts, cotton swabs, gauze), expired or discarded medicines, pharmaceutical waste, cytotoxic drugs along with reagents, chemical waste, and discarded linen/beddings contaminated with blood.
        - Segregation Receptacle: Non-chlorinated yellow plastic bags or containers.
        - Approved Treatment & Disposal: Incineration at high temperature (primary chamber 800°C, secondary chamber 1050°C) or plasma pyrolysis. Cytotoxic drugs must be returned to manufacturer or incinerated at >1200°C. Never dispose of Yellow waste in municipal landfills.

        2. RED CATEGORY:
        - Applicable Waste Items: Contaminated recyclable plastic waste generated from disposable medical devices such as tubing sets, intravenous (IV) drip bottles and tubing, catheters, urine bags, disposable syringes without needles, vacutainers, dialysis kits, and clean examination gloves.
        - Segregation Receptacle: Non-chlorinated red plastic bags or autoclavable red containers.
        - Approved Treatment & Disposal: Autoclaving or micro-waving followed by shredding or mutilation. The shredded plastic waste is sent to registered plastic recyclers. Shredding prevents illegal reuse of medical plastics.

        3. WHITE (TRANSLUCENT) CATEGORY - SHARPS:
        - Applicable Waste Items: Waste sharps including needles, syringes with fixed needles, needles from needle tip cutter or burner, scalpels, surgical blades, lancets, trocars, suture needles, and any contaminated sharp metal objects capable of causing puncture or cuts.
        - Segregation Receptacle: Puncture-proof, tamper-proof, leak-proof translucent or white containers.
        - Approved Treatment & Disposal: Autoclaving or dry heat sterilization followed by shredding, mutilation, or encapsulation in concrete pit. Sharps must never be recapped manually to prevent needle-stick injuries.

        4. BLUE CATEGORY:
        - Applicable Waste Items: Broken or intact contaminated glassware including medicine vials, ampoules (except those containing cytotoxic drugs), laboratory slides, glass specimen bottles, and metallic body implants (orthopedic pins, plates, screws, nails).
        - Segregation Receptacle: Puncture-proof and leak-proof blue boxes or cardboard boxes with blue marking.
        - Approved Treatment & Disposal: Disinfection by soaking in 1% to 2% Sodium Hypochlorite solution or autoclaving/microwaving, followed by recycling.
        """

        hospital_sop_text = """
        HOSPITAL INFECTION CONTROL COMMITTEE (HICC) - STANDARD OPERATING PROCEDURE (SOP-BMW-04)
        BIONEX AUTONOMOUS ROBOTIC WASTE COLLECTION SYSTEM

        SECTION 1: BED-SIDE AND WARD WASTE PROTOCOLS
        - The 75% Fill Rule: Waste bags and containers must be sealed and collected when they are 3/4th (75%) full. Under no circumstances should containers be allowed to overflow.
        - Zero-Recap Policy: Used needles must NEVER be recapped, bent, or broken by hand. Use the needle hub cutter or drop directly into the White puncture-proof sharps container.
        - Liquid Waste: Blood and liquid body fluids must not be poured down general sinks without prior chemical disinfection with 1% sodium hypochlorite for minimum 20 minutes.

        SECTION 2: BIONEX AUTONOMOUS ROBOT HANDOVER SEQUENCE
        1. Staff initiates collection request via BioNex staff portal selecting ward, room, and waste category.
        2. BioNex AMR navigates along designated hospital corridor routes using Nav2 obstacle avoidance.
        3. Upon arrival at ward, staff places waste into the enclosed robotic input tray.
        4. Internal high-resolution camera and tray presence sensor activate.
        5. The vision system inspects the item. Deterministic validation verifies eligibility.
        6. Only the single designated compartment gate opens (Yellow, Red, White, or Blue). Other three gates remain electromechanically interlocked.
        7. Drop sensor verifies passage into sealed compartment. Gate immediately seals.
        
        SECTION 3: UNIDENTIFIED, MIXED, OR HAZARDOUS WASTE PROCEDURE
        - If waste is mixed (e.g. sharp needle stuck inside plastic tubing), leaking radioactive or cytotoxic fluid, or unidentifiable by the vision model (confidence < 85%):
          * The BioNex robotic arm immediately halts all manipulation.
          * The item remains inside the enclosed intake chamber.
          * A High-Priority 'Human Review' alert is broadcast to the ward nurse and Infection Control Officer.
          * The robot will NEVER force-separate mixed or jammed items.
          * Trained infection control staff must inspect with level-3 PPE and manually resolve the categorization.
        """

        safety_manual_text = """
        BIONEX AUTONOMOUS MOBILE ROBOT (AMR) - SYSTEM ARCHITECTURE & SAFETY SPECIFICATIONS
        
        SECTION 1: HARDWARE ARCHITECTURE & SENSOR SUITE
        - Mobile Base: Geared DC motors driven by TB6612FNG H-bridge motor driver, optical wheel encoders, and front/rear bumper switches.
        - Compute Nodes: Jetson/Raspberry Pi for vision AI inference and high-level ROS 2 navigation; ESP32 microcontroller for low-level motor PWM, ultrasonic distance radar, tray presence switch (HX711/GPIO18), and PCA9685 I2C 16-channel PWM servo controller.
        - Hardware Safety Interlocks: Physical Emergency Stop button breaks battery actuator power rail directly via relay. Software cannot override a triggered physical E-Stop.
        - Compartments: Four sealed compartments lined with non-reactive antimicrobial coating. White compartment features reinforced puncture-resistant steel-backed liner.

        SECTION 2: AGENTIC AI DECISION HIERARCHY
        - Collection Agent: Validates request parameters and schedules tasks based on urgency.
        - Route/Emergency Agent: Dynamically prioritizes trauma/emergency calls over routine collection, coordinating corridor clearance.
        - Segregation Agent: Validates vision proposals against statutory CPCB rules. If ambiguous, flags for Human Review.
        - Monitoring Agent: Telemetry watchdog that continuously reads battery level and ultrasonic bin fill sensors. When any bin reaches 80% or battery drops below 20%, AMR transitions to return-to-dock mode.
        """

        spill_protocol_text = """
        EMERGENCY SPILL MANAGEMENT & POST-EXPOSURE PROPHYLAXIS (PEP) PROTOCOL
        
        SECTION 1: BLOOD OR INFECTIOUS FLUID SPILL PROCEDURE
        1. Evacuate immediate patient area and place biohazard warning cones.
        2. Don complete PPE: double nitrile gloves, fluid-resistant gown, surgical mask, and eye protection goggles.
        3. Cover spill completely with absorbent paper towels to contain spread.
        4. Pour 1% freshly prepared Sodium Hypochlorite solution (10,000 ppm available chlorine) around and onto the paper towels.
        5. Allow contact time of at least 20 minutes for complete microbial kill.
        6. Clean up soaked towels and place into Yellow biomedical waste bag.
        7. Mop area with hospital-grade disinfectant.

        SECTION 2: NEEDLE-STICK INJURY IMMEDIATE ACTION
        - Wash the injured site immediately with copious soap and running water.
        - DO NOT squeeze or rub the wound.
        - Do not use antiseptic soap or scrub with harsh brushes.
        - Report immediately to Hospital Infection Control Officer within 1 hour.
        - Initiate Post-Exposure Prophylaxis (PEP) within 2 hours of exposure if indicated.
        """

        all_docs = [
            ("CPCB Bio-Medical Waste Management Rules 2016", "Schedule I & Regulations", cpcb_text, 1),
            ("Hospital Infection Control SOP (SOP-BMW-04)", "Ward Protocols & AMR Handover", hospital_sop_text, 1),
            ("BioNex AMR Safety & Hardware Specifications", "Robotics & Hardware Interlocks", safety_manual_text, 1),
            ("Emergency Spill & Post-Exposure Protocol", "Spill Response & Needle-Stick PEP", spill_protocol_text, 1),
        ]

        for title, section, text, start_page in all_docs:
            chunks = self._split_into_chunks(text, title, section, start_page)
            self.chunks.extend(chunks)

        self._build_index()

    def _build_index(self):
        """Builds TF-IDF term weights for all chunks."""
        doc_count = len(self.chunks)
        if doc_count == 0:
            return

        term_doc_counts: Dict[str, int] = {}
        
        for chunk in self.chunks:
            tokens = self.tokenize(chunk.content)
            term_freqs: Dict[str, int] = {}
            for t in tokens:
                term_freqs[t] = term_freqs.get(t, 0) + 1
            
            chunk.terms = {t: 1.0 + math.log(cnt) for t, cnt in term_freqs.items()}
            for t in set(tokens):
                term_doc_counts[t] = term_doc_counts.get(t, 0) + 1

        self.idf = {
            t: math.log((doc_count + 1) / (count + 1)) + 1.0
            for t, count in term_doc_counts.items()
        }

        for chunk in self.chunks:
            norm_sq = 0.0
            for t, tf in chunk.terms.items():
                w = tf * self.idf.get(t, 1.0)
                chunk.terms[t] = w
                norm_sq += w * w
            norm = math.sqrt(norm_sq) if norm_sq > 0 else 1.0
            for t in chunk.terms:
                chunk.terms[t] /= norm

        self.initialized = True

    def add_document(self, title: str, text: str, file_type: str = "PDF") -> int:
        chunks = self._split_into_chunks(text, title, "Uploaded Document", 1)
        self.chunks.extend(chunks)
        self._build_index()
        return len(chunks)

    def retrieve(self, query: str, top_k: int = 4) -> List[Tuple[DocumentChunk, float]]:
        if not self.initialized:
            self._load_knowledge_base()

        query_tokens = self.tokenize(query)
        if not query_tokens:
            return []

        q_tf: Dict[str, float] = {}
        for t in query_tokens:
            q_tf[t] = q_tf.get(t, 0) + 1.0

        q_vec: Dict[str, float] = {}
        norm_sq = 0.0
        for t, cnt in q_tf.items():
            w = (1.0 + math.log(cnt)) * self.idf.get(t, 1.0)
            q_vec[t] = w
            norm_sq += w * w
        
        norm = math.sqrt(norm_sq) if norm_sq > 0 else 1.0
        for t in q_vec:
            q_vec[t] /= norm

        scores: List[Tuple[DocumentChunk, float]] = []
        for chunk in self.chunks:
            dot_product = 0.0
            for t, q_val in q_vec.items():
                if t in chunk.terms:
                    dot_product += q_val * chunk.terms[t]
            if dot_product > 0.01:
                scores.append((chunk, dot_product))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def ask(self, query: str) -> Dict[str, Any]:
        results = self.retrieve(query, top_k=3)

        if not results or results[0][1] < 0.08:
            return {
                "query": query,
                "answer": "The BioNex knowledge base does not contain verified regulatory or SOP information on this query. Under hospital safety rules, the system will not invent biomedical guidelines. Please consult the Hospital Infection Control Committee (HICC) or your floor supervisor.",
                "confidence_score": 0.0,
                "citations": [],
                "status": "unverified"
            }

        top_chunk, best_score = results[0]
        citations = []
        context_snippets = []

        for chunk, score in results:
            citations.append({
                "document": chunk.doc_name,
                "section": chunk.section,
                "page": chunk.page,
                "chunk_id": chunk.chunk_id,
                "relevance": round(score * 100, 1),
                "snippet": chunk.content[:200] + "..."
            })
            context_snippets.append(chunk.content)

        answer = self._synthesize_answer(query, context_snippets, top_chunk)

        return {
            "query": query,
            "answer": answer,
            "confidence_score": round(best_score * 100, 1),
            "citations": citations,
            "status": "verified"
        }

    def _synthesize_answer(self, query: str, context: List[str], top_chunk: DocumentChunk) -> str:
        q_lower = query.lower()

        if "needle" in q_lower or "syringe" in q_lower or "sharp" in q_lower:
            return (
                "According to CPCB Bio-Medical Waste Rules (2016) and Hospital SOP-BMW-04: "
                "Waste sharps such as needles, syringes with fixed needles, scalpels, and blades MUST be placed in the "
                "WHITE (Translucent) puncture-proof, leak-proof container. "
                "Crucial Safety Rule: Needles must NEVER be recapped, bent, or broken manually to prevent needle-stick injury. "
                "Treatment is dry-heat sterilization / autoclaving followed by shredding or encapsulation."
            )
        elif "yellow" in q_lower or "anatomical" in q_lower or "soiled" in q_lower:
            return (
                "YELLOW Category waste includes human and animal anatomical waste, soiled dressings, gauze swabs contaminated with blood or body fluids, "
                "expired/discarded medicines, and cytotoxic pharmaceuticals. "
                "Receptacle: Non-chlorinated yellow plastic bags. "
                "Treatment: Incineration at 1050°C (secondary chamber) or plasma pyrolysis. Never send Yellow waste to landfills."
            )
        elif "red" in q_lower or "plastic" in q_lower or "iv tube" in q_lower or "catheter" in q_lower or "glove" in q_lower:
            return (
                "RED Category waste is reserved for contaminated recyclable plastics: IV tubing, IV bottles, catheters, urine bags, "
                "syringes WITHOUT needles, and disposable clean examination gloves. "
                "Receptacle: Non-chlorinated red autoclavable bags. "
                "Treatment: Autoclaving/microwaving followed by mechanical shredding, and subsequent handover to registered plastic recyclers."
            )
        elif "blue" in q_lower or "glass" in q_lower or "vial" in q_lower or "ampoule" in q_lower or "implant" in q_lower:
            return (
                "BLUE Category waste comprises contaminated or broken glassware (medicine vials, ampoules without cytotoxic residue, microscope slides) "
                "and metallic body implants (orthopedic screws, plates, pins). "
                "Receptacle: Puncture-proof blue boxes or cardboard containers with blue branding. "
                "Treatment: Disinfection by soaking in 1% sodium hypochlorite or autoclaving, followed by recycling."
            )
        elif "four" in q_lower and ("category" in q_lower or "categories" in q_lower or "waste" in q_lower):
            return (
                "The four statutory biomedical waste categories under CPCB 2016 Rules are:\n"
                "1. YELLOW: Anatomical, soiled, pharmaceutical, cytotoxic waste (Incineration 1050°C).\n"
                "2. RED: Contaminated recyclable plastics such as IV tubes, catheters, gloves (Autoclave + Shredding).\n"
                "3. WHITE (Translucent): Puncture-proof container for sharps, needles, surgical blades (Sterilization + Encapsulation).\n"
                "4. BLUE: Glassware, ampoules, vials, and metallic orthopedic implants (Chemical Disinfection / Recycling)."
            )
        elif "unidentified" in q_lower or "mixed" in q_lower or "unsafe" in q_lower or "unsure" in q_lower or "procedure" in q_lower:
            return (
                "Procedure for Unidentified, Mixed, or Unsafe Waste (Hospital SOP-BMW-04 Section 3):\n"
                "1. The BioNex robotic arm immediately halts physical manipulation.\n"
                "2. The enclosed intake chamber remains securely locked.\n"
                "3. An automatic High-Priority 'Human Review' alert is sent to the ward nurse and Infection Control Officer.\n"
                "4. The robot will NEVER force-separate mixed, tangled, or leaking items.\n"
                "5. Only trained healthcare staff donning Level-3 PPE are authorized to manually inspect and segregate the item."
            )
        elif "spill" in q_lower or "blood spill" in q_lower:
            return (
                "Blood / Infectious Fluid Spill Protocol:\n"
                "1. Don full PPE (double gloves, fluid-resistant gown, mask, goggles).\n"
                "2. Cover spill completely with absorbent towels to prevent spreading.\n"
                "3. Apply 1% freshly prepared Sodium Hypochlorite solution (10,000 ppm chlorine).\n"
                "4. Maintain contact time of at least 20 minutes before cleanup.\n"
                "5. Dispose of soaked paper towels in the YELLOW biohazard bag."
            )
        else:
            return (
                f"Based on {top_chunk.doc_name} ({top_chunk.section}, Page {top_chunk.page}):\n\n"
                f"{top_chunk.content[:400]}...\n\n"
                "Note: BioNex advisory systems provide strictly approved hospital guidelines. Always follow designated infection control policies."
            )


# Global singleton instance
rag_engine = BiomedicalRAGEngine()
