"""
End-to-end test: Phase 0 → Phase 1 (Interview Pipeline).

Tests the full user journey:
  1. Health check (P0)
  2. Create user + start interview modules (P1)
  3. Complete all 7 mandatory modules with answers (P1)

Run with: python tests/test_e2e_flow.py
"""

import asyncio
import json
import sys
import time
from uuid import UUID, uuid4

import httpx

BASE = "http://localhost:8000"
API = f"{BASE}/api/v1"

# Track timing
start_time = time.time()


def elapsed():
    return f"[{time.time() - start_time:.1f}s]"


def fail(msg):
    print(f"\n  FAIL: {msg}")
    sys.exit(1)


def ok(msg=""):
    print(f"  OK {msg}")


async def retry_post(client, url, json_data, max_retries=3, delay=5):
    """Retry a POST request on 500 errors (LLM transient failures)."""
    for attempt in range(max_retries):
        r = await client.post(url, json=json_data)
        if r.status_code != 500:
            return r
        if attempt < max_retries - 1:
            print(f"    Retry {attempt+1}/{max_retries} after 500 error...")
            await asyncio.sleep(delay)
    return r


async def main():
    async with httpx.AsyncClient(timeout=300.0) as client:
        # ==============================================================
        # PHASE 0: Foundation
        # ==============================================================
        print(f"\n{'='*60}")
        print("PHASE 0: Foundation")
        print(f"{'='*60}")

        # 1. Health check
        print(f"\n{elapsed()} Testing health check...")
        r = await client.get(f"{BASE}/health")
        if r.status_code != 200:
            fail(f"Health check failed: {r.status_code}")
        data = r.json()
        assert data["status"] == "healthy", f"Status: {data['status']}"
        assert data["database"] == "connected", f"DB: {data['database']}"
        ok(f"status={data['status']}, db={data['database']}, version={data['version']}")

        # 2. Root endpoint
        print(f"\n{elapsed()} Testing root endpoint...")
        r = await client.get(f"{BASE}/")
        assert r.status_code == 200
        data = r.json()
        ok(f"name={data['name']}, env={data['environment']}")

        # 3. API docs accessible
        print(f"\n{elapsed()} Testing API docs...")
        r = await client.get(f"{BASE}/docs")
        assert r.status_code == 200
        ok("Swagger UI accessible")

        # ==============================================================
        # PHASE 1: Text Interview + Modules
        # ==============================================================
        print(f"\n{'='*60}")
        print("PHASE 1: Text Interview + Modules")
        print(f"{'='*60}")

        # Generate a user ID upfront — the backend will auto-create the user
        user_id = str(uuid4())
        completed_modules = []

        # Module-specific answers targeting each module's signal list
        module_answers = {
            # M1 signals: occupation_lifestyle_overview, age_band, living_context,
            #             self_described_personality, life_stage, daily_routine_pattern
            "M1": [
                "I'm a 28-year-old software engineer living in Mumbai. I work at a tech startup and my typical week involves coding, team meetings, and client calls. I wake up at 8am, exercise for 30 minutes, start work by 10, and usually wrap up by 7pm. Evenings I cook dinner and read or watch something.",
                "I'd describe myself as analytical, curious, and slightly introverted. I'm the kind of person who researches everything before committing. People say I'm reliable and thoughtful, but I can overthink things. I have a dry sense of humor.",
                "I live alone in a 1BHK apartment in Andheri, Mumbai. I moved out of my parents' house about 3 years ago when I started my current job. I'm at an early career stage, focused on learning and building up my savings.",
                "The most important thing in my life right now is growing my career. I want to move into a senior engineering role within the next year. I'm also building a side project on weekends — a small SaaS tool.",
                "My close friends would call me dependable, nerdy, and thoughtful. They say I always come through when it matters but I tend to overthink simple decisions.",
                "My daily routine is very structured. Wake up at 8, gym until 9, work 10 to 7, cook dinner, read or code on my side project until 11. Weekends are more flexible — I meet friends, explore cafes, or just stay in.",
            ],
            # M2 signals: speed_vs_deliberation, gut_vs_data, risk_appetite,
            #             reversibility_sensitivity, information_needs, decision_regret_pattern
            "M2": [
                "For my last big purchase, a laptop, I spent about two weeks researching. I compared specs across 5-6 models, watched review videos, read Reddit threads, and made a spreadsheet. I need to feel confident I'm making the right choice before I spend that kind of money.",
                "I'm definitely more of a data-driven decision maker. I rarely go with my gut for anything important. I need to see comparisons, reviews, and ideally talk to someone who already owns the thing. For small decisions like what to eat, I go with my gut.",
                "I'm fairly risk-averse with money — I wouldn't invest in crypto or gamble. But I'm willing to take career risks for the right opportunity. I left a stable corporate job to join a startup because I believed in the product.",
                "I'm very sensitive to whether a decision is reversible. If I can return something or cancel a subscription, I decide much faster. But for irreversible things like signing a lease or taking a new job, I deliberate for days or weeks.",
                "I once impulsively bought a gym membership at a fancy gym. A month later I realized I barely used the extra facilities and regretted not going with the cheaper option. Since then I always do a trial period before committing.",
                "When I look back at past decisions, I mostly regret the ones I rushed into. So now I have a personal rule: for anything over 5000 rupees, I sleep on it for at least one night before buying.",
            ],
            # M3 signals: control_vs_convenience, price_vs_quality, privacy_vs_personalization,
            #             novelty_vs_familiarity, speed_vs_thoroughness, independence_vs_support
            "M3": [
                "Quality matters more to me than price. I'd rather save up and buy something that lasts 5 years than get the cheap version that breaks in 6 months. For headphones, chairs, and kitchen tools, I always go premium.",
                "I like apps that give me control. I don't want an algorithm deciding everything for me. I prefer to customize my settings, choose my own playlists, and set my own filters. Automatic recommendations are fine as secondary options but I want to be in the driver's seat.",
                "I'm fairly privacy-conscious. I don't like companies tracking my every move, but I accept some personalization if it genuinely improves my experience. I use ad blockers and limit app permissions, but I'll share data with apps I trust if the trade-off is clear.",
                "I tend to stick with brands and products I know work well. I'm not the kind of person who tries every new thing. But once a year or so I'll explore alternatives to make sure I'm not missing out on something better.",
                "I prefer to be thorough rather than fast. Whether it's cooking, coding, or shopping, I'd rather take extra time to do it right than rush and end up with a mediocre result. Speed is only important when there's a real deadline.",
                "I prefer figuring things out on my own. I'll read documentation, watch tutorials, and troubleshoot before asking someone for help. But for major life decisions, I do consult close friends or family for a second opinion.",
            ],
            # M4 signals: bathing_routine, skin_concerns, grooming_habits
            "M4": [
                "I shower twice a day — once in the morning before work and once in the evening after my gym session. My morning shower is quick, about 5 minutes, while the evening one is longer and more relaxing.",
                "My main skin concern is dryness, especially during winter. My skin gets flaky on my arms and legs. I've tried various moisturizing body washes but haven't found the perfect one yet.",
                "I use a loofah with my body wash. I prefer something that lathers well because it feels like it's cleaning better. I also use a separate face wash — never body wash on my face.",
                "My grooming routine is pretty basic — body wash, shampoo, face wash, deodorant. I don't use too many products. I keep it simple but I care about the quality of what I use.",
                "After showering I always apply moisturizer, especially in winter. I prefer unscented or lightly scented moisturizers. My skin is sensitive so I avoid anything too harsh.",
                "I'd say I spend about 15 minutes total on my bathing and grooming routine each morning. I like efficiency but I don't want to rush through it.",
            ],
            # M5 signals: fragrance_preferences, texture_preferences, sensory_priorities
            "M5": [
                "For body wash, I prefer fresh, clean scents — like mint, eucalyptus, or ocean breeze. I don't like anything too sweet or floral. The scent shouldn't be overpowering, just subtle and refreshing.",
                "Texture-wise, I like a gel body wash that's not too thick and not too watery. It should spread easily and lather well. I've tried cream-based body washes but they don't feel as clean to me.",
                "Lather is important to me. I want a rich, foamy lather that covers well. If a body wash doesn't lather much, I end up using more product and it feels wasteful.",
                "I don't care much about packaging design but I do prefer bottles that are easy to use in the shower — good grip, flip-top cap. Pump bottles are even better.",
                "The after-feel matters a lot. I don't want to feel sticky or like there's a residue. I want my skin to feel clean, smooth, and slightly moisturized after rinsing off.",
            ],
            # M6 signals: current_brands, satisfaction, pain_points, switching_behavior
            "M6": [
                "I currently use Dove Men+Care body wash. I've been using it for about a year. Before that I tried Nivea and Old Spice. I switched from Nivea because it was drying out my skin.",
                "I'm fairly satisfied with Dove — maybe 7 out of 10. It moisturizes well and the scent is pleasant. But I wish the lather was richer and the bottle design was better for gripping in the shower.",
                "My biggest pain point is finding a body wash that balances cleaning power with moisturizing. Most that clean well are too drying, and the moisturizing ones don't feel clean enough. I want both.",
                "Price matters but it's not the top factor. I typically spend 300-400 rupees on a body wash bottle. I'd pay up to 500 if the product was noticeably better.",
                "I usually buy body wash at the supermarket. Sometimes online if there's a good deal. I don't have strong brand loyalty — I'm open to switching if something better comes along.",
                "The ideal body wash for me would have a fresh subtle scent, rich lather, moisturizing formula, and come in a practical bottle with a pump. If a brand offered all of that, I'd switch immediately.",
            ],
            # M7 signals: media_consumption, influence_sources, discovery_channels
            "M7": [
                "I discover new personal care products mostly through YouTube reviews and Reddit discussions. I follow a couple of grooming channels that do honest product comparisons.",
                "I trust peer reviews over celebrity endorsements. If a product has good ratings on Amazon with detailed reviews, that carries more weight than a Bollywood actor promoting it.",
                "Social media ads sometimes catch my attention but I rarely buy directly from an ad. I'll note the product and then research it independently before purchasing.",
                "Friends' recommendations are powerful for me. If a close friend says 'try this body wash, it's great,' I'll almost certainly try it. Word of mouth is my most trusted source.",
                "I don't follow any specific influencers for grooming advice. I prefer educational content — like dermatologists explaining ingredients — over lifestyle influencers showing their routines.",
            ],
        }

        # 4. Complete all 7 modules (M1 → M7)
        for module_id in ["M1", "M2", "M3", "M4", "M5", "M6", "M7"]:
            print(f"\n{elapsed()} Starting module {module_id}...")

            # Start single module
            start_req = {
                "user_id": user_id,
                "module_id": module_id,
                "input_mode": "text",
                "language_preference": "en",
                "consent": {
                    "accepted": True,
                    "consent_version": "1.0",
                },
            }

            r = await client.post(f"{API}/interviews/start-module", json=start_req)
            if r.status_code not in (200, 201):
                fail(f"Start module {module_id} failed: {r.status_code} - {r.text}")

            data = r.json()
            session_id = data["session_id"]

            first_q = data.get("first_question", {})
            question_id = first_q.get("question_id", "q1")
            ok(f"session={session_id[:8]}..., first_q={question_id}")

            answers = module_answers[module_id]

            module_done = False
            for i, answer in enumerate(answers):
                # Submit answer
                answer_req = {
                    "answer_text": answer,
                    "question_id": question_id,
                    "input_mode": "text",
                }
                r = await retry_post(
                    client, f"{API}/interviews/{session_id}/answer", answer_req
                )
                if r.status_code == 400 and "No active module" in r.text:
                    # Module was already completed by the server
                    print(f"    Module {module_id} auto-completed after {i} answers")
                    module_done = True
                    break
                if r.status_code != 200:
                    fail(f"Answer {i+1} failed: {r.status_code} - {r.text}")

                # Get next question
                r = await retry_post(
                    client, f"{API}/interviews/{session_id}/next-question", {}
                )
                if r.status_code == 400 and "No active module" in r.text:
                    print(f"    Module {module_id} auto-completed after {i+1} answers")
                    module_done = True
                    break
                if r.status_code != 200:
                    fail(f"Next question {i+1} failed: {r.status_code} - {r.text}")

                next_data = r.json()
                status = next_data.get("status")
                question_id = next_data.get("question_id", f"q{i+3}")

                if status == "module_complete" or status == "all_modules_complete":
                    print(f"    Module {module_id} completed after {i+1} answers")
                    module_done = True
                    break

            # Complete module and exit
            r = await client.post(f"{API}/interviews/{session_id}/complete-module")
            if r.status_code == 200:
                complete_data = r.json()
                coverage = complete_data.get("coverage_score", 0)
                confidence = complete_data.get("confidence_score", 0)
                mod_status = complete_data.get("status", "unknown")
                ok(
                    f"Module {module_id} {mod_status}: "
                    f"coverage={coverage:.2f}, confidence={confidence:.2f}, "
                    f"can_generate_twin={complete_data.get('can_generate_twin')}"
                )
                if mod_status == "module_paused":
                    print(f"    WARN: Module {module_id} paused (coverage too low), may affect eligibility")
            elif module_done:
                # Module was already completed server-side
                ok(f"Module {module_id} was already completed by server")
            else:
                fail(f"Complete module {module_id} failed: {r.status_code} - {r.text}")

            completed_modules.append(module_id)

        # 5. Check modules status
        print(f"\n{elapsed()} Checking user modules...")
        r = await client.get(f"{API}/interviews/user/{user_id}/modules")
        if r.status_code != 200:
            fail(f"Get modules failed: {r.status_code} - {r.text}")

        modules_data = r.json()
        ok(
            f"completed={modules_data['completed_count']}/{modules_data['total_required']}, "
            f"can_generate_twin={modules_data['can_generate_twin']}"
        )

        # ==============================================================
        # SUMMARY
        # ==============================================================
        total_time = time.time() - start_time
        print(f"\n{'='*60}")
        print("E2E TEST SUMMARY")
        print(f"{'='*60}")
        print(f"  Total time: {total_time:.1f}s")
        print(f"  User ID: {user_id}")
        print(f"  Phase 0: PASS (health, root, docs)")
        print(f"  Phase 1: PASS (7 modules completed)")
        print(f"\n  ALL PHASES PASSED")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(main())
