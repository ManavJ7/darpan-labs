"""Phase 3 variant definitions (prosumer / SMB IT / consumer).

Imported for side-effects: each module-level call to
`register_phase` wires the variant into the state machine's lookup
table. Splitting out to keep phase_defs.py shorter and the v1 item
inventory easy to scan.
"""

from __future__ import annotations

from app.services.phase_defs import BlockDef, ItemDef, PhaseDef, register_phase


def _jtbd_open(code: str, phase: str, block: str, prompt: str, purpose: str,
               probing_hints: list[str] | None = None, max_probes: int = 2) -> ItemDef:
    return ItemDef(
        id=f"{phase}.{code}",
        module_code=code,
        phase=phase,
        block=block,
        kind="open",
        prompt=prompt,
        purpose=purpose,
        probing_hints=probing_hints or [],
        max_probes=max_probes,
    )


def _conjoint_block(phase: str, archetype: str, code_prefix: str) -> BlockDef:
    items: list[ItemDef] = []
    for i in range(8):
        code = f"{code_prefix}_C{i+1}"
        items.append(ItemDef(
            id=f"{phase}.{code}",
            module_code=code,
            phase=phase,
            block="conjoint",
            kind="conjoint",
            prompt=("Here are three realistic laptop offers. Pick the one "
                    "you'd actually choose in real life."),
            purpose=("Choice-based conjoint set — part-worth estimation "
                     "input. Alternatives are pre-rendered by the widget "
                     "resolver keyed by session_id."),
            widget={"type": "conjoint_set", "set_index": i, "archetype": archetype},
            max_probes=0,  # structured; no LLM probing needed
        ))
    return BlockDef(
        id="conjoint",
        phase=phase,
        label="Choice-based conjoint",
        budget_minutes=10,
        items=items,
    )


def _brand_block(phase: str, archetype: str, code_prefix: str) -> BlockDef:
    b1 = ItemDef(
        id=f"{phase}.{code_prefix}_B1",
        module_code=f"{code_prefix}_B1",
        phase=phase,
        block="brand",
        kind="open",
        prompt=("Off the top of your head — if you had to name laptop "
                "brands you can think of, go ahead. Up to five."),
        purpose="Unaided brand recall. Count + order matter.",
        max_probes=0,
    )
    b2 = ItemDef(
        id=f"{phase}.{code_prefix}_B2",
        module_code=f"{code_prefix}_B2",
        phase=phase,
        block="brand",
        kind="slider_matrix",
        prompt=("For each brand below, rate how well each statement "
                "describes it. You can tick 'don't know this brand' "
                "for any row."),
        purpose=("Brand association lattice — archetype-specific "
                 "attribute set."),
        widget={"type": "brand_lattice", "archetype": archetype},
        max_probes=0,
    )
    return BlockDef(
        id="brand",
        phase=phase,
        label="Brand perception lattice",
        budget_minutes=6,
        items=[b1, b2],
    )


def _tone_block(phase: str, archetype: str, code_prefix: str) -> BlockDef:
    t1 = ItemDef(
        id=f"{phase}.{code_prefix}_T1",
        module_code=f"{code_prefix}_T1",
        phase=phase,
        block="tone",
        kind="tone_pair",
        prompt="Pick the ad that feels more like a brand you'd take seriously, and tell me why in a sentence.",
        purpose="Tone preference pair A.",
        widget={"type": "tone_pair", "pair": "pair_a", "archetype": archetype},
        max_probes=1,
    )
    t2 = ItemDef(
        id=f"{phase}.{code_prefix}_T2",
        module_code=f"{code_prefix}_T2",
        phase=phase,
        block="tone",
        kind="tone_pair",
        prompt="Same again — which feels more like a brand you'd take seriously, and why.",
        purpose="Tone preference pair B.",
        widget={"type": "tone_pair", "pair": "pair_b", "archetype": archetype},
        max_probes=1,
    )
    t3 = ItemDef(
        id=f"{phase}.{code_prefix}_T3",
        module_code=f"{code_prefix}_T3",
        phase=phase,
        block="tone",
        kind="projective",
        prompt="(projective close — LLM uses archetype-specific text)",
        purpose=("Projective peer-advice prompt. Reveals latent "
                 "brand beliefs via third-party framing."),
        max_probes=2,
    )
    return BlockDef(
        id="tone",
        phase=phase,
        label="Creative tone + projective",
        budget_minutes=4,
        items=[t1, t2, t3],
    )


# --------------------------- Phase 3a — Prosumer ----------------------------

PROSUMER_JTBD = BlockDef(
    id="jtbd",
    phase="phase3a",
    label="Purchase episode reconstruction",
    budget_minutes=13,
    items=[
        _jtbd_open(
            "A_J1", "phase3a", "jtbd",
            "Take me back to the last time you got a new laptop. What was the first moment you realized you were going to need a new one?",
            "Trigger moment. Probe: how long did you tolerate the old one? what tipped you over?",
            ["If short or vague, ask: 'how long did you tolerate the old one before that moment?' or 'what tipped you over?'"],
        ),
        _jtbd_open(
            "A_J2", "phase3a", "jtbd",
            "In the weeks or months before you actually bought something — what were you doing to work around the problem? Any hacks, workarounds, ways you were putting up with it?",
            "Compensating behaviors — reveals the pain that eventually drove the hire.",
            ["If 'nothing', ask: 'so what actually stopped you from buying sooner?' — surfaces anxiety forces."],
        ),
        _jtbd_open(
            "A_J3", "phase3a", "jtbd",
            "Once you decided to get a new one — what laptops (or types of laptops) did you seriously consider? Walk me through the options that were actually in the running.",
            "Considered set. Brands + specific models + types.",
        ),
        _jtbd_open(
            "A_J4", "phase3a", "jtbd",
            "Were there laptops or brands you didn't even bother looking into? Ones you just wouldn't consider? Why not?",
            "Rejected set — highest-signal question. Surfaces strong brand biases.",
        ),
        _jtbd_open(
            "A_J5", "phase3a", "jtbd",
            "Did you ask anyone for advice — coworkers, online reviews, YouTube, friends, IT? Walk me through what you looked at.",
            "Information diet + influencers.",
        ),
        _jtbd_open(
            "A_J6", "phase3a", "jtbd",
            "What was the final decision — and what was the moment or thing that actually made you click buy (or request it, or accept what IT issued)?",
            "Clincher. Often surfaces a non-obvious tie-breaker.",
        ),
        _jtbd_open(
            "A_J7", "phase3a", "jtbd",
            "In the first month with the new laptop, what felt better? What, if anything, surprised you — good or bad?",
            "Post-purchase satisfaction / surprise signals.",
        ),
        _jtbd_open(
            "A_J8", "phase3a", "jtbd",
            "If you had to describe, in your own words, what this laptop needed to DO for you in your life — not just its specs, but the role it plays — how would you put it?",
            "The JTBD statement. Probe for 2-3 rounds if needed. Good jobs are specific.",
            ["Probe for specificity. A good JTBD is concrete: 'survive a 14-hour travel day', 'not make me look cheap in client meetings'."],
            max_probes=3,
        ),
    ],
)

register_phase(PhaseDef(
    id="phase3a",
    label="Prosumer body",
    budget_minutes=33,
    archetype="prosumer",
    blocks=[
        PROSUMER_JTBD,
        _conjoint_block("phase3a", "prosumer", "A"),
        _brand_block("phase3a", "prosumer", "A"),
        _tone_block("phase3a", "prosumer", "A"),
    ],
))


# --------------------------- Phase 3b — SMB IT ------------------------------

SMB_JTBD = BlockDef(
    id="jtbd",
    phase="phase3b",
    label="Fleet purchase episode reconstruction",
    budget_minutes=13,
    items=[
        _jtbd_open(
            "B_J1", "phase3b", "jtbd",
            "Walk me back to the last time you bought laptops for your team. What prompted it — was it a refresh, a new hire wave, a specific problem?",
            "Trigger for fleet purchase.",
        ),
        _jtbd_open(
            "B_J2", "phase3b", "jtbd",
            "Before that purchase — what was bothering you about the current fleet? Complaints you were hearing, issues you were fixing, things that were breaking?",
            "Fleet pain points.",
        ),
        _jtbd_open(
            "B_J3", "phase3b", "jtbd",
            "When you started looking — who were you talking to? Vendors, resellers, peer IT leaders, online? What was your information diet?",
            "Info sources — reseller relationships matter for SMB.",
        ),
        _jtbd_open(
            "B_J4", "phase3b", "jtbd",
            "Which brands made it to your shortlist? Which ones you didn't even call — and why not?",
            "Considered + rejected sets. Rejection is often about support relationships, not taste.",
            ["Probe into specific support incidents behind rejections."],
        ),
        _jtbd_open(
            "B_J5", "phase3b", "jtbd",
            "Did anyone else have a say — the CFO, the CEO, the team that would use them? How was that dynamic?",
            "DMU dynamics.",
        ),
        _jtbd_open(
            "B_J6", "phase3b", "jtbd",
            "What clinched it? Was it price, support terms, a relationship, a demo, employee preference, or something else?",
            "Clincher for fleet.",
        ),
        _jtbd_open(
            "B_J7", "phase3b", "jtbd",
            "Six months in — was it the right call? Any issues, any pleasant surprises?",
            "Post-purchase outcome.",
        ),
        _jtbd_open(
            "B_J8", "phase3b", "jtbd",
            "If you had to describe what these laptops need to DO for your team — and what problems they need to NOT cause you — how would you put it?",
            "Twin JTBD: functional job for user + anxiety-management job for buyer.",
            ["Probe both halves: user-side job AND buyer-side job."],
            max_probes=3,
        ),
    ],
)

register_phase(PhaseDef(
    id="phase3b",
    label="SMB IT buyer body",
    budget_minutes=33,
    archetype="smb_it",
    blocks=[
        SMB_JTBD,
        _conjoint_block("phase3b", "smb_it", "B"),
        _brand_block("phase3b", "smb_it", "B"),
        _tone_block("phase3b", "smb_it", "B"),
    ],
))


# --------------------------- Phase 3c — Consumer ----------------------------

CONSUMER_JTBD = BlockDef(
    id="jtbd",
    phase="phase3c",
    label="Personal purchase episode",
    budget_minutes=13,
    items=[
        _jtbd_open(
            "C_J1", "phase3c", "jtbd",
            "Think about the last laptop you bought for yourself or your family. When was it, and what was going on in your life at the time?",
            "Life-event framing matters for consumers. Probe for life context, not just device.",
        ),
        _jtbd_open(
            "C_J2", "phase3c", "jtbd",
            "Before you bought it — what were you using? What was annoying you about it, or what did the new one need to solve?",
            "Prior device + pain.",
        ),
        _jtbd_open(
            "C_J3", "phase3c", "jtbd",
            "When you started looking — where did you look? YouTube? Amazon reviews? Best Buy? A friend or family member? Walk me through the research.",
            "Info sources.",
        ),
        _jtbd_open(
            "C_J4", "phase3c", "jtbd",
            "Which laptops did you seriously consider? Which ones did you dismiss quickly — and why?",
            "Considered + rejected sets.",
        ),
        _jtbd_open(
            "C_J5", "phase3c", "jtbd",
            "How much did you care about the price? Was there a budget you had set, and did the final purchase stay under it?",
            "Budget salience — much higher for consumers. Probe stretch-vs-stick behavior.",
        ),
        _jtbd_open(
            "C_J6", "phase3c", "jtbd",
            "Did you talk it over with anyone — spouse, partner, family, friends? Who had influence on the decision?",
            "Influence dynamics.",
        ),
        _jtbd_open(
            "C_J7", "phase3c", "jtbd",
            "What sealed the deal? Was it a specific feature, a review, the price, the look, someone's recommendation?",
            "Clincher.",
        ),
        _jtbd_open(
            "C_J8", "phase3c", "jtbd",
            "A few months later — was it the right choice? What do you love, what do you wish you'd known?",
            "Post-purchase satisfaction.",
        ),
        _jtbd_open(
            "C_J9", "phase3c", "jtbd",
            "If you had to describe what this laptop needs to DO in your life — beyond the specs — what would you say?",
            "The JTBD statement. Probe for specificity.",
            max_probes=3,
        ),
    ],
)

register_phase(PhaseDef(
    id="phase3c",
    label="Consumer body",
    budget_minutes=33,
    archetype="consumer",
    blocks=[
        CONSUMER_JTBD,
        _conjoint_block("phase3c", "consumer", "C"),
        _brand_block("phase3c", "consumer", "C"),
        _tone_block("phase3c", "consumer", "C"),
    ],
))
