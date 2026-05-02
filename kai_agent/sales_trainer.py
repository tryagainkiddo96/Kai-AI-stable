"""
Kai Sales Command Center — NCL Auto Brokers Wolf of Wall Street System.

Complete all-in-one sales workshop: scripts, objection handlers, tracking,
training workshops, bump selling, dealer management, and the Wolf mindset.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


# ========================
# DATA MODELS
# ========================

@dataclass
class SalesScript:
    id: str
    name: str
    category: str
    phase: int  # 1-11 matching NCL process
    script: str
    tone: str
    variations: List[str] = field(default_factory=list)
    success_tips: List[str] = field(default_factory=list)
    kill_shots: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "category": self.category,
            "phase": self.phase, "script": self.script, "tone": self.tone,
            "variations": self.variations, "success_tips": self.success_tips,
            "kill_shots": self.kill_shots,
        }


@dataclass
class ObjectionKillShot:
    objection: str
    kill_shot: str
    follow_up: str
    alternative: str = ""

    def to_dict(self) -> dict:
        return {
            "objection": self.objection, "kill_shot": self.kill_shot,
            "follow_up": self.follow_up, "alternative": self.alternative,
        }


@dataclass
class DealRecord:
    deal_id: str
    date: str
    customer_name: str
    phone: str = ""
    email: str = ""
    vehicle: str = ""
    msrp: float = 0.0
    hot_button: str = ""
    target_payment: float = 0.0
    quoted_payment: float = 0.0
    status: str = "discovery"  # discovery, built, quote, committed, finding, closed, paid, lost
    broker_fee: float = 399.0
    cc_captured: bool = False
    credit_app: str = "pending"
    trade: str = "no"
    trade_value: float = 0.0
    next_action: str = ""
    next_action_date: str = ""
    closed_date: str = ""
    commission: float = 0.0
    paid: bool = False
    notes: str = ""

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class DealerRecord:
    dealership: str
    contact: str = ""
    phone: str = ""
    works_with_brokers: bool = True
    max_fee: float = 500.0
    out_of_state: bool = True
    hard_adds: str = ""
    last_contact: str = ""
    notes: str = ""
    best_deal: str = ""

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


# ========================
# SALES COMMAND CENTER
# ========================

class KaiSalesCommandCenter:
    """
    Complete Wolf of Wall Street Sales Command Center for NCL Auto Brokers.
    Scripts, objection handlers, deal tracking, training, bump selling, dealer management.
    """

    NCL_PHASES = {
        1: "Make Contact — Lead calls, email, text, follow-up",
        2: "Discovery — Qualify, explain service, paint the dream",
        3: "Build the Car — Manufacturer website, build code, hot button",
        4: "Initial Quote / Four Square — Payment math, trade, desking",
        5: "Get Commitment — DocuSign, credit card, credit app, documents",
        6: "Find the Car — Dealer contacts, Cars.com, invoice, crop VIN",
        7: "Final Close — Re-desk, close on found car, new DocuSign",
        8: "BFA — Broker Fee Agreement to dealer, credit packet, bump sell",
        9: "Get Money Get Paid — Run CC, coordinate delivery, check request",
        10: "Thank You & Reviews — Yelp/Google, referrals",
        11: "Cilajet Order — If sold, order the installation",
    }

    PAYMENT_MATH = {
        "per_1000_options": 20,
        "per_1000_rebate": 30,
        "zero_drive_off_multiplier": 2.5,
    }

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace
        self.data_path = workspace / "memory" / "sales_command_center.json"
        self.data_path.parent.mkdir(parents=True, exist_ok=True)

        self.scripts: Dict[str, SalesScript] = {}
        self.objections: List[ObjectionKillShot] = []
        self.deals: Dict[str, DealRecord] = {}
        self.dealers: Dict[str, DealerRecord] = {}
        self.company_info: Dict[str, Any] = {}
        self.training_log: List[Dict] = []
        self.leaderboard: List[Dict] = []
        self.choke_log: List[Dict] = []

        self._load_data()
        if not self.scripts:
            self._init_wolf_system()

    def _load_data(self) -> None:
        if self.data_path.exists():
            try:
                data = json.loads(self.data_path.read_text(encoding="utf-8"))
                for sid, sdata in data.get("scripts", {}).items():
                    self.scripts[sid] = SalesScript(**sdata)
                for odata in data.get("objections", []):
                    self.objections.append(ObjectionKillShot(**odata))
                for ddata in data.get("deals", {}).values():
                    self.deals[ddata["deal_id"]] = DealRecord(**ddata)
                for ddata in data.get("dealers", {}).values():
                    self.dealers[ddata["dealership"]] = DealerRecord(**ddata)
                self.company_info = data.get("company_info", {})
                self.training_log = data.get("training_log", [])
                self.leaderboard = data.get("leaderboard", [])
                self.choke_log = data.get("choke_log", [])
            except Exception:
                pass

    def _save_data(self) -> None:
        data = {
            "scripts": {k: v.to_dict() for k, v in self.scripts.items()},
            "objections": [o.to_dict() for o in self.objections],
            "deals": {k: v.to_dict() for k, v in self.deals.items()},
            "dealers": {k: v.to_dict() for k, v in self.dealers.items()},
            "company_info": self.company_info,
            "training_log": self.training_log[-100:],
            "leaderboard": self.leaderboard,
            "choke_log": self.choke_log[-50:],
            "updated_at": datetime.utcnow().isoformat(),
        }
        self.data_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _init_wolf_system(self) -> None:
        """Initialize the complete Wolf of Wall Street NCL Auto Brokers system."""
        scripts = [
            # PHASE 1: MAKE CONTACT
            SalesScript(
                id="inbound_opener",
                name="Inbound Call Opener — Pattern Interrupt",
                category="opening", phase=1,
                tone="confident",
                script=(
                    'YOU: "Hi [Customer], this is [Name] with [Company]. How are you today?"\n\n'
                    'CUSTOMER: "Good, thanks."\n\n'
                    'YOU: "I received your inquiry on the [Year Make Model]. Is now a good time to talk for about 7 minutes?"\n\n'
                    "[If yes, continue. If no, schedule EXACT callback time]\n\n"
                    'YOU: "Perfect. Look, you probably have a lot of questions. Here\'s what I\'m going to do — '
                    "let me ask you a few questions first. I'll answer yours along the way, "
                    "and I usually answer things most people forget to ask. Fair?\"\n\n"
                    'CUSTOMER: "Sure."'
                ),
                success_tips=[
                    "Get agreement on 7 minutes upfront",
                    "Control the frame — you ask, they answer",
                    "If they barrage with questions, use the 'let me ask a few first' line",
                ],
                variations=[
                    '"I only need 90 seconds. Three questions. You answer honestly. Then I\'ll tell you if I can save you $3,000 or you should hang up and call a dealer. Deal?"',
                    '"You don\'t know me. You don\'t know if I\'m full of sh*t or if I can actually save you money. That would be stupid to buy from me right now. Give me 7 minutes and you decide."',
                ],
            ),
            SalesScript(
                id="just_looking_assassin",
                name='The "Just Looking" Assassin',
                category="opening", phase=1,
                tone="disarming",
                script=(
                    'CUSTOMER: "I\'m just looking right now. Not ready to buy."\n\n'
                    'YOU: "I wouldn\'t expect you to be ready to buy. You don\'t know me. '
                    "You don't know if I'm full of sh*t or if I can actually save you money. "
                    "That would be stupid.\n\n"
                    "Here's what I want — 7 minutes on the phone. You ask me anything. "
                    "I'll show you real numbers on the car you want. At the end of 7 minutes, "
                    "you decide if I'm full of sh*t or if I just saved you $3,000. Fair?\"\n\n"
                    "[They always say yes — you just disarmed them with honesty]\n\n"
                    'YOU: "Great. Question 1 — Have you ever used a car broker before?"'
                ),
                success_tips=[
                    "Acknowledge their position — don't fight it",
                    "Disarm with radical honesty",
                    "The 7-minute frame is powerful — use it",
                ],
            ),
            SalesScript(
                id="referral_opener",
                name="Referral Opener — Highest Conversion",
                category="opening", phase=1,
                tone="warm_confident",
                script=(
                    'YOU: "Hey [Name], this is [You] from [Company]. '
                    "[Mutual Contact] said you might be looking for a [car type].\n\n"
                    "They also said you're the kind of person who doesn't like wasting time "
                    "or getting screwed at dealerships. That sound about right?\"\n\n"
                    'CUSTOMER: "Yeah, that\'s me."\n\n'
                    'YOU: "Perfect. [Mutual Contact] is one of our favorite clients. '
                    "Here's what I promised them — I would treat you exactly like I treated them.\n\n"
                    "That means real numbers, no games, and a car delivered to your door. Sound fair?\"\n\n"
                    "[They're already sold — referral trust transfers immediately]\n\n"
                    'YOU: "Then let\'s spend 5 minutes and build your car. When do you need it by?"'
                ),
                success_tips=[
                    "Referral trust transfers immediately — use it",
                    "Reference the mutual contact by name",
                    "Move to building the car fast",
                ],
            ),

            # PHASE 2: DISCOVERY
            SalesScript(
                id="discovery_interrogation",
                name="The Discovery Interrogation — All 10 Questions",
                category="discovery", phase=2,
                tone="professional_direct",
                script=(
                    'YOU: "Let me get to know what you need. Quick questions — answer honestly and I\'ll save you the most money."\n\n'
                    "Q1: Have you HIRED a service like ours before, or have you always bought through a dealership?\n"
                    "Q2: Most people don't enjoy buying a new car. What was your experience like LAST time? Be honest — I've heard everything.\n"
                    "Q3: On a scale of 1 to 10, how much did you HATE that process?\n"
                    "Q4: What's the REAL reason you're looking for a new car right now?\n"
                    "Q5: What's your DREAM version of this car? If money were no object, what would you build?\n"
                    "Q6: What's your NIGHTMARE scenario with buying a car?\n"
                    "Q7: Who else is involved in this decision?\n"
                    "Q8: What payment would make you say 'THAT'S A DEAL — LET'S DO IT'?\n"
                    "Q9: Do you know your credit score? A 720 or above qualifies for our best specials.\n"
                    'Q10: Are you okay with us shipping from 500 or even 2000 miles away if the deal is better?'
                ),
                success_tips=[
                    "Ask ALL 10 — no exceptions",
                    "Write down every answer",
                    "Listen for the HOT BUTTON",
                    "Use their pain points later in the pitch",
                ],
            ),
            SalesScript(
                id="paint_the_dream",
                name="Paint the Dream — Value Stack Pitch",
                category="presentation", phase=2,
                tone="confident_visionary",
                script=(
                    'YOU: "So here\'s how this works, [Name]. There are two ways to get a new car:\n\n'
                    "OPTION 1: You go to a dealership. You spend 4 hours waiting. "
                    "You deal with a salesman who 'checks with his manager' six times. "
                    "They bring out the four-square. They add nitrogen in tires for $500. "
                    "You leave wondering if you got screwed.\n\n"
                    "OPTION 2: You hire us. We bypass the retail internet department and work "
                    "directly with upper management at Penske, Fletcher Jones, and AutoNation.\n\n"
                    "We get real numbers upfront. We deliver to your home or office within 72 hours. "
                    "We stay with you from beginning to end so dealerships never have a chance to up-sell you.\n\n"
                    "And here's the kicker — our clients typically save $3,000 to $5,000. "
                    "That's $90 to $150 per month — more than enough to cover our fee.\n\n"
                    "[PAUSE]\n\n"
                    "Everyone loves having a new car. Everyone HATES buying a new car. "
                    "We remove the 'buying' part.\n\n"
                    'Sound like something you\'d want?"'
                ),
                success_tips=[
                    "PAUSE after the pitch — let it land",
                    "Reference their specific pain points from discovery",
                    "Use their exact words when possible",
                ],
                variations=[
                    "I'm not selling you a car. I'm selling you 4 hours of your life back, your sanity, your time, and your money. What's YOUR time worth?",
                ],
            ),

            # PHASE 3: BUILD THE CAR
            SalesScript(
                id="build_session",
                name="The Build Session — Stay on the Phone",
                category="building", phase=3,
                tone="collaborative",
                script=(
                    'YOU: "I\'m going to walk you through the manufacturer website right now. '
                    "I'm sending you a link — can you open it while we're on the phone?\"\n\n"
                    "[CUSTOMER opens link]\n\n"
                    "YOU: What colors have you seen that you really like? Give me your top 3, in order.\n\n"
                    "YOU: Okay, I'm selecting [Color 1]. For interior — light or dark? Leather or cloth?\n\n"
                    "YOU: Now packages. What are MUST-HAVES for you?\n"
                    "- Heated seats?\n- Sunroof?\n- Premium audio?\n- Safety features?\n- Cold weather package?\n\n"
                    "[Note each one. Every option adds $20/month per $1000.]\n\n"
                    "YOU: Everyone has a HOT BUTTON — what's most important to you?\n"
                    "SAFETY for the family? FUEL ECONOMY for your commute? "
                    "POWER and performance? LUXURY and comfort? Or STATUS?\n\n"
                    "[They pick one. WRITE IT DOWN. This is your closing lever.]\n\n"
                    "YOU: Perfect. I'm building this now. Here's your build code: [XXXXXX].\n\n"
                    "I'm going to email you the build sheet PDF — you just need to reply 'APPROVED' "
                    "when you get it, or tell me what to change."
                ),
                success_tips=[
                    "Stay on the phone the entire time",
                    "Find the HOT BUTTON — write it on a sticky note",
                    "Get the build code",
                    "Email the PDF immediately",
                ],
            ),

            # PHASE 4: INITIAL QUOTE
            SalesScript(
                id="initial_quote_foursquare",
                name="Initial Quote — Four Square Over Phone",
                category="quoting", phase=4,
                tone="confident_analytical",
                script=(
                    "[BEFORE CALLING — Do the math:]\n"
                    "Base payment from ad car: $349\n"
                    "Added options: $3,000 = +$60 ($20 per $1000)\n"
                    "Cash/rebate: $2,000 = -$60 ($30 per $1000)\n"
                    "Total: $349 + tax\n\n"
                    'YOU: "[Name], based on the car you built. MSRP is $[XXX] compared to our advertised car at $[XXX].\n\n'
                    "The difference is $[XXX]. That adds about $[XX] per month.\n\n"
                    "So your payment would be around $[XXX] plus tax, with $2,500 out of pocket at signing.\n\n"
                    'That includes your first payment, registration, fees, and our service fee rolled in.\n\n'
                    'HOW DOES THAT SOUND TO YOU?"\n\n'
                    "[Listen carefully — they'll tell you if they've shopped]\n\n"
                    'CUSTOMER: "That\'s a bit higher than I was hoping."\n\n'
                    'YOU: "What have you been seeing locally?"\n\n'
                    "[They give you a number — this is gold]\n\n"
                    'YOU: "Okay, I can work on that. Here\'s what I need to know — '
                    "what's the ULTIMATE payment that fits your budget?\n"
                    "Give me a number where you say 'YES, let's do this' and I'll see if we can get there. Be honest.\"\n\n"
                    'YOU: "And if I get you that exact number with $2,500 drive-off, are you ready to move forward TODAY?"'
                ),
                success_tips=[
                    "Know your math cold: $20 per $1000 options, $30 per $1000 down",
                    "Ask what they've been seeing locally — valuable intel",
                    "Get their TRUE budget number",
                    "Ask for commitment IF you hit that number",
                ],
            ),

            # PHASE 5: GET COMMITMENT
            SalesScript(
                id="assumptive_close",
                name="The Assumptive Close — Use 80% of the Time",
                category="closing", phase=5,
                tone="confident_assumptive",
                script=(
                    "[After handling objections and agreeing on numbers]\n\n"
                    'YOU: "Perfect. So here\'s what\'s going to happen next.\n\n'
                    "I'm going to send you a Docusign right now — it's our Broker Agreement. "
                    "It outlines everything we discussed: the car, the colors, the payment range, our $595 fee.\n\n"
                    "You're going to sign it.\n\n"
                    "Then you're going to send me three things:\n"
                    "- A picture of your Driver's License — front and back\n"
                    "- A recent pay stub or proof of income\n"
                    "- A utility bill for proof of residence\n\n"
                    "Then I'm going to find YOUR exact car within 24 hours and lock this deal.\n\n"
                    'Should I send the Docusign to [email address] or [different email]?"\n\n'
                    "[Notice: You never asked IF they want to proceed. You asked HOW they want to proceed.]\n\n"
                    'CUSTOMER: "[Email address]"\n\n'
                    'YOU: "Sending now. Stay on the line while you get it — takes 2 minutes.\n\n'
                    'Also — I need a credit card to hold the deal. $595 for our full service. '
                    "Should I use Visa or Mastercard?\"\n\n"
                    '[If they hesitate: "The card just holds your build spot. I don\'t charge until you approve the actual car. Fair?"]\n\n'
                    "[Then stay on the phone until the Docusign is signed AND you have the credit card.]"
                ),
                success_tips=[
                    "Never ask IF — ask HOW",
                    "Stay on the phone until signed",
                    "Get the credit card on the same call",
                    "Walk them through the Docusign live",
                ],
            ),
            SalesScript(
                id="either_or_close",
                name='The "Either/Or" Close',
                category="closing", phase=5,
                tone="confident_binary",
                script=(
                    'YOU: "We\'ve got two ways to do this.\n\n'
                    "Option A: You sign today, I find your car this week, "
                    "you're driving it by [day of week].\n\n"
                    "Option B: You think about it, I move on to other clients, "
                    "and next week when you call me back the car might be gone "
                    "or the lease program might change.\n\n"
                    'Which option works better for you?"'
                ),
                success_tips=[
                    "Both options should lead to a close",
                    "Option B creates urgency without being pushy",
                    "Make Option A obviously better",
                ],
            ),
            SalesScript(
                id="take_away_close",
                name='The "Take It Away" Close — For Stubborn Prospects',
                category="closing", phase=5,
                tone="challenging",
                script=(
                    'YOU: "You know what, [Name] — I don\'t think this is for you.\n\n'
                    "Most of our clients are decision-makers. They see value, they act, "
                    "and they're driving their car within a week.\n\n"
                    "I get the sense you're more of a 'thinker' — which is fine. "
                    "But I've got other clients waiting who ARE ready to move.\n\n"
                    "So tell you what — take my card. When you're ready to stop thinking "
                    "and start driving, give me a call. Sound fair?\"\n\n"
                    "[This triggers loss aversion. They will stop you 80% of the time.]\n\n"
                    'CUSTOMER: "Wait, hold on — I didn\'t say I wasn\'t interested..."\n\n'
                    'YOU: "Oh? So you ARE ready to move forward today? '
                    'Because I\'m happy to help if you are."'
                ),
                success_tips=[
                    "Only use this when you've built real value",
                    "Be willing to actually walk away",
                    "Triggers loss aversion — powerful",
                    "Follow up immediately if they stop you",
                ],
            ),
            SalesScript(
                id="columbo_close",
                name='The "Columbo" Close — One More Thing',
                category="closing", phase=5,
                tone="casual_urgent",
                script=(
                    '[After they say "let me think about it"]\n\n'
                    'YOU: "Hey, one more thing — I almost forgot.\n\n'
                    "[Wait for them to lean in]\n\n"
                    "The reason I called you today specifically — there's a program that ends "
                    "[Friday/end of month]. Honda/BMW/Mercedes is offering an additional "
                    "$1,000 rebate but ONLY for deals locked by [date].\n\n"
                    "I didn't want to lead with that because I don't want you to make a decision "
                    "based on pressure. But I also didn't want you to call me next week and "
                    "find out the deal is gone.\n\n"
                    'So knowing THAT — does that change anything for you?"\n\n'
                    "[Then shut up. Let them process. They will often close themselves.]"
                ),
                success_tips=[
                    "Say 'one more thing' — makes them lean in",
                    "Frame it as helpful, not pressure",
                    "Then SHUT UP — let them close themselves",
                ],
            ),

            # PHASE 6-7: FIND THE CAR & FINAL CLOSE
            SalesScript(
                id="found_the_car_close",
                name="Found the Car — Final Close",
                category="closing", phase=7,
                tone="excited_confident",
                script=(
                    'YOU: "[Name] — GOOD NEWS. I found YOUR car.\n\n'
                    "[Dealership name redacted — never reveal] has a "
                    "[Year Make Model Trim] in [Color] with [Key packages].\n\n"
                    "It's [XX] miles away and they'll deliver to your door.\n\n"
                    "Here are the REAL numbers:\n"
                    "- MSRP: $[XXX]\n"
                    "- Your payment: $[XXX] INCLUDING tax\n"
                    "- Out of pocket at signing: $[XXX]\n"
                    "- Miles per year: [XX]\n"
                    "- Term: [XX] months\n\n"
                    "[PAUSE — let it land]\n\n"
                    'YOU: "Can I lock this in for you TODAY?"\n\n'
                    "[If yes]\n\n"
                    'YOU: "Amazing.\n\n'
                    "Here's what happens now — I'm sending the BFA to the dealership. "
                    "Once they sign, I send YOUR credit packet over to them.\n\n"
                    "They'll call you to verify identity — that's it. No negotiation. "
                    "No upselling. Just 'yes, that's me' and you're approved.\n\n"
                    "Delivery scheduled for [Day].\n\n"
                    '[Name] — you just made the smartest car-buying decision of your life. '
                    'Welcome to the family."'
                ),
                success_tips=[
                    "Never reveal the dealership name",
                    "Present the numbers cleanly",
                    "PAUSE after the numbers",
                    "Assume the close",
                    "Make them feel like they won",
                ],
            ),

            # PHASE 8: BUMP SELLING
            SalesScript(
                id="bump_sell_cilajet",
                name="Bump Sell — Cilajet Ceramic Coating",
                category="bump_selling", phase=8,
                tone="casual_helpful",
                script=(
                    "[AFTER closing the main deal — this is pure profit]\n\n"
                    'YOU: "Hey [Name] — one thing I almost forgot. Three out of four of our '
                    "clients add this, so I want to at least offer it.\n\n"
                    "CILAJET — it's a ceramic coating that protects your paint from bird droppings, "
                    "UV rays, and minor scratches. Normally $895 at the dealership. We get it for $495.\n\n"
                    "Want me to add it? Can roll it into your payment — adds about $14/month.\"\n\n"
                    '[If yes: "Done. I\'m sending an updated Docusign. Smart move."]\n\n'
                    '[If no: "No problem. Let me ask you about LEASE END PROTECTION..."]'
                ),
                success_tips=[
                    "Timing is everything — ask immediately after they say yes",
                    "Frame it as something 'most clients add'",
                    "Roll into payment — makes it painless",
                    "Your commission: 50-100% on bump products",
                ],
            ),
            SalesScript(
                id="bump_sell_platinum",
                name="Bump Sell — Platinum Protection Package",
                category="bump_selling", phase=8,
                tone="value_stack",
                script=(
                    'YOU: "Actually [Name] — let me tell you about our PLATINUM PROTECTION PACKAGE.\n\n'
                    "For $1,495 — which is only $995 more than our standard fee — you get:\n\n"
                    "- Cilajet ceramic coating ($495 value)\n"
                    "- Lease end protection ($399 value)\n"
                    "- Excess miles waiver — 3,000 extra miles ($299 value)\n"
                    "- Gap insurance ($299 value)\n"
                    "- AND we waive your next broker fee ($595 value)\n\n"
                    "Total value: over $2,000. You pay $995 more than standard.\n\n"
                    "That's basically FREE.\n\n"
                    "And here's the best part — you can roll the ENTIRE thing into your payment. "
                    "Adds about $28/month.\n\n"
                    "For less than $1 a day, you never worry about:\n"
                    "- Paint damage\n- Turn-in fees\n- Going over miles\n- Being upside down in an accident\n\n"
                    'Most of our clients upgrade to Platinum. Should I send that agreement instead?"'
                ),
                success_tips=[
                    "This is a $1,000+ bump commission — sell it hard",
                    "Stack the value to make it feel free",
                    "Roll into payment — removes friction",
                    "Use 'most clients upgrade' — social proof",
                ],
            ),

            # PHASE 10: THANK YOU & REFERRALS
            SalesScript(
                id="thank_you_referral",
                name="Thank You & Referral Close",
                category="followup", phase=10,
                tone="warm_enthusiastic",
                script=(
                    "[AFTER delivery — call or text within 24 hours]\n\n"
                    'YOU: "Hey [Name]! Heard the car was delivered. How\'s it FEEL?"\n\n'
                    "[Listen to excitement — they always have it]\n\n"
                    'CUSTOMER: "It\'s amazing! Thank you so much."\n\n'
                    'YOU: "That\'s awesome. That\'s why we do this.\n\n'
                    "Hey — two quick favors for letting me save you $3,000:\n\n"
                    "1. Would you leave us a Google or Yelp review? Mention my name — [Your Name]. "
                    "It takes 2 minutes and helps other people avoid dealership hell.\n\n"
                    '2. Who do you know that\'s looking for a car? We pay $[XXX] for every referral '
                    "that closes. Text me their name and number — I'll take it from there "
                    "and never bother you again.\n\n"
                    'Who comes to mind?"\n\n'
                    "[Get at least one name. Text them immediately]\n\n"
                    'YOU: "One more name? You\'re helping two friends."'
                ),
                success_tips=[
                    "Ask for TWO referrals, not one",
                    "Text the referral immediately",
                    "Time it when they're most excited (delivery day)",
                    "Mention the referral bonus",
                ],
            ),

            # TEXT SCRIPTS
            SalesScript(
                id="text_initial",
                name="Text — Initial Contact",
                category="text", phase=1,
                tone="casual",
                script=(
                    'Hey [Name]! This is [Your Name] from [Company]. '
                    "Got your inquiry on the [Make Model]. Quick question — "
                    "leased before or first time? Got 2 mins to chat?"
                ),
            ),
            SalesScript(
                id="text_followup_24h",
                name="Text — 24h Follow-up (No Response)",
                category="text", phase=1,
                tone="urgent_casual",
                script=(
                    "[Name], you still looking for that [Make Model]? "
                    "Found a dealer with special financing that ends Friday. "
                    "Let me know if you want me to hold the rate for you."
                ),
            ),
            SalesScript(
                id="text_after_quote",
                name="Text — After Quote Sent",
                category="text", phase=4,
                tone="competitive",
                script=(
                    "[Name], got numbers back on that [Make]. "
                    "$[XXX]/mo with $[XXX] DAS including tax. "
                    "What are you seeing locally? Happy to beat it by $50/mo or I owe you $100."
                ),
            ),
            SalesScript(
                id="text_closing",
                name="Text — Deal Locked (Victory Lap)",
                category="text", phase=7,
                tone="excited",
                script=(
                    "[Name] — DEAL IS LOCKED! 🚗 Delivery scheduled for [Day]. "
                    "Tracking coming shortly. Welcome to the family. Tell your friends about me 😎"
                ),
            ),
            SalesScript(
                id="text_alive_check",
                name='Text — "Are You Alive?" (3 days no response)',
                category="text", phase=1,
                tone="playful_urgent",
                script=(
                    '[Name] — you alive? 😂 Seriously though — the lease program on that '
                    "[Make] changed today. Went up $45/mo. Let me know if you still want me "
                    "to look or if I should move on."
                ),
            ),

            # DEALER SCRIPTS
            SalesScript(
                id="dealer_cold_call",
                name="Dealer Cold Call — New Relationship",
                category="dealer", phase=6,
                tone="confident_direct",
                script=(
                    'YOU: "Hey [Dealer Name], this is [Your Name] with [Company].\n\n'
                    "Two things before I take too much of your time:\n\n"
                    "One — I send about [X] deals a month to my top 3 dealers.\n"
                    "Two — I don't waste time. I send clean credit, approved buyers, "
                    "and I don't nickel and dime.\n\n"
                    "Question for you — do you want more of those deals, "
                    "or are you good with what you've got?\"\n\n"
                    'DEALER: "I always want more deals."\n\n'
                    'YOU: "Then here\'s what I need to know in 60 seconds:\n\n'
                    "- Do you work with brokers? Yes or no?\n"
                    "- What's your max broker fee?\n"
                    "- Can I quote my customers at buyrate?\n"
                    "- Do you do out-of-state deals?\n"
                    "- What hard adds do I need to warn my clients about?\n\n"
                    'Answer those, and I\'ll send you a deal THIS WEEK. Fair?"'
                ),
                success_tips=[
                    "Get straight to the point — dealers respect time",
                    "Lead with volume — they want deals",
                    "If they say no, ask who DOES work with brokers",
                    "Get inventory with invoice pricing",
                ],
            ),
            SalesScript(
                id="dealer_active_deal",
                name="Dealer Follow-Up — Active Deal (High Urgency)",
                category="dealer", phase=6,
                tone="urgent_direct",
                script=(
                    'YOU: "Hey [Dealer Name], [Your Name] from [Company]. '
                    "Working a deal on Stock # [XXX] — the [Make Model].\n\n"
                    "Three questions:\n\n"
                    "One — is it still available?\n"
                    "Two — what's your BEST broker number on it?\n"
                    "Three — can you deliver to [ZIP] and what's the fee?\n\n"
                    "I have a QUALIFIED buyer ready to go TODAY. Clean credit. 750 score. "
                    "Ready to sign.\n\n"
                    "I just need numbers I can work with. Give me something aggressive "
                    "and I close them in an hour.\n\n"
                    'What do you got?"'
                ),
                success_tips=[
                    "Lead with qualified buyer — creates urgency",
                    "Be prepared to walk if numbers don't work",
                    "Split the difference to close the dealer",
                    "Get the invoice and crop out dealer name",
                ],
            ),
        ]

        for s in scripts:
            self.scripts[s.id] = s

        # OBJECTION KILL SHOTS
        self.objections = [
            ObjectionKillShot(
                objection="Let me think about it",
                kill_shot=(
                    "I completely understand. But here's what usually happens — "
                    "you hang up, life gets busy, and two weeks from now you're still driving "
                    "your old car wishing you had made the switch.\n\n"
                    "What SPECIFICALLY do you need to think about?\n\n"
                    "If it's the payment, let's talk payment. "
                    "If it's the car, let's find a different car. "
                    "If it's me — fair enough, I haven't earned your trust yet.\n\n"
                    "So tell me the REAL objection, and I'll address it. Because "
                    "'let me think about it' is what people say when they don't want to say "
                    "what's REALLY bothering them.\n\n"
                    "What's REALLY going on?"
                ),
                follow_up="[THEN SHUT UP. Silence is your weapon. They will tell you.]",
            ),
            ObjectionKillShot(
                objection="I need to ask my spouse",
                kill_shot=(
                    "Of course you do. That's smart. Big decisions should be made together.\n\n"
                    "Here's what I recommend — let's get your spouse on a 3-way call right now. "
                    "I'll explain everything once. Takes 5 minutes. Then you two can talk privately "
                    "and call me back.\n\n"
                    "Is [spouse name] available? Or should I call back in an hour when they're home?"
                ),
                follow_up='[If they hesitate: "Or... are YOU the decision-maker and you\'re using them as an excuse?"]\n\n[If they admit it: "Then let\'s not waste time. Sign now. Tell them later you got an incredible deal. They\'ll be proud."]',
            ),
            ObjectionKillShot(
                objection="I want to check with local dealers",
                kill_shot=(
                    "You absolutely should. In fact, I encourage it.\n\n"
                    "Here's what I want you to do — go to three dealers. Get their best number. "
                    "Write it down.\n\n"
                    "Then call me. I will beat their best deal by AT LEAST $500, "
                    "or I will pay YOU $500. I'm that confident.\n\n"
                    "But here's the catch — you have to do it in the next 48 hours. "
                    "Because the lease program I'm looking at expires [Friday/end of month].\n\n"
                    'Deal?"'
                ),
                follow_up="[They either commit to the challenge or just buy from you now.]",
            ),
            ObjectionKillShot(
                objection="Your fee is too high",
                kill_shot=(
                    "Let me ask you something. If I save you $3,000 on the car, "
                    "and my fee is $595... how much did you SAVE?\n\n"
                    'CUSTOMER: "$2,405."\n\n'
                    'YOU: "So you\'re telling me you wouldn\'t pay $595 to save $2,405? '
                    "That's a 400% return on investment.\n\n"
                    "What if I told you you could invest $595 and get back $2,405 in 1 week? "
                    'Would you do it?"\n\n'
                    'CUSTOMER: "Yes."\n\n'
                    'YOU: "Then the fee isn\'t too high. You just haven\'t seen the savings yet. '
                    'Let me show you..."'
                ),
                follow_up="[Then SHOW the numbers. Stack the savings. Close.]",
            ),
            ObjectionKillShot(
                objection="I don't give my credit card over the phone",
                kill_shot=(
                    "I wouldn't either. There are too many scammers.\n\n"
                    "But here's how you know I'm legit — I'm not asking for the full amount. "
                    "I'm going to send you a SECURE Docusign link. You enter your card THERE, "
                    "not to me over the phone.\n\n"
                    "And if after I send you real numbers on a real car within 24 hours you're "
                    "not HAPPY... you call your bank, dispute the charge, and I never call you again.\n\n"
                    'Fair? Then let\'s do this."'
                ),
                follow_up="[Send the Docusign immediately. Stay on the line until they open it.]",
            ),
            ObjectionKillShot(
                objection="That payment is higher than I expected",
                kill_shot=(
                    "What have you BEEN seeing locally? Be honest.\n\n"
                    "[They give a number — usually unrealistic]\n\n"
                    "I understand. Here's the reality — the advertised specials you see are on "
                    "BASE models with NO options, $5,000+ due at signing, and before tax and fees.\n\n"
                    "The car you built has [list 3 options]. That adds about $[XX]/month.\n\n"
                    "But here's what I can do — let me see if there's a similar car with fewer "
                    "options, or a different color that's on sale.\n\n"
                    "What's more important to you — the [Option 1] or the payment?"
                ),
                follow_up="[Then find the compromise. Or show them the value again.]",
            ),
            ObjectionKillShot(
                objection="I'm not ready to buy for 3 months",
                kill_shot=(
                    "I respect that. Here's what I recommend — let's get you set up in our system "
                    "NOW, lock in today's rates with a small deposit, and then when you ARE ready, "
                    "you don't have to start over.\n\n"
                    "Because here's what happens in 3 months — rates might be higher, "
                    "rebates might be gone, and the car might cost you $50 more per month.\n\n"
                    "Give me $200 today to lock your build. Fully refundable if you change your mind.\n\n"
                    "Worst case — you're out $200. Best case — you save $1,800 over 3 years.\n\n"
                    'Which sounds better to you?"'
                ),
                follow_up="",
            ),
            ObjectionKillShot(
                objection="I found a better deal elsewhere",
                kill_shot=(
                    "Great! Seriously — I love when my clients shop. It keeps me honest.\n\n"
                    "Two questions —\n\n"
                    "One: Are you comparing the SAME car? Same MSRP, same options, "
                    "same miles, same drive-off?\n\n"
                    "Two: Did the dealer give you that number in WRITING or was it verbal?\n\n"
                    "Because here's what dealers do — they quote you a low number over the phone, "
                    "you drive 2 hours to get there, and suddenly the car has $2,000 in "
                    "'mandatory add-ons' and your payment jumps $80.\n\n"
                    "I'll give you that same number RIGHT NOW in writing. No games. No hidden fees.\n\n"
                    "Send me their quote — I'll beat it or I'll pay you $500.\n\n"
                    'What\'s their number?"'
                ),
                follow_up="",
            ),
        ]

        self._save_data()

    # ========================
    # SCRIPT RETRIEVAL
    # ========================

    def get_scripts_by_phase(self, phase: int) -> List[SalesScript]:
        """Get all scripts for a specific NCL phase."""
        return [s for s in self.scripts.values() if s.phase == phase]

    def get_scripts_by_category(self, category: str) -> List[SalesScript]:
        """Get scripts by category."""
        return [s for s in self.scripts.values() if s.category == category]

    def get_script(self, script_id: str) -> Optional[SalesScript]:
        """Get a specific script by ID."""
        return self.scripts.get(script_id)

    def find_objection(self, customer_input: str) -> Optional[ObjectionKillShot]:
        """Find the best objection handler for customer input."""
        input_lower = customer_input.lower()
        for oh in self.objections:
            if oh.objection.lower() in input_lower:
                return oh
        # Partial match
        for oh in self.objections:
            words = oh.objection.lower().split()
            if any(w in input_lower for w in words if len(w) > 3):
                return oh
        return None

    def get_all_phases(self) -> Dict[int, str]:
        """Get the complete 11-phase NCL process."""
        return self.NCL_PHASES

    # ========================
    # PAYMENT MATH
    # ========================

    def calculate_payment(
        self, base_payment: float, options_msrp: float = 0,
        rebate_or_down: float = 0, zero_drive_off: bool = False,
    ) -> float:
        """
        Calculate lease payment using NCL formulas.
        $20 per $1000 in options, $30 per $1000 in rebate/down,
        $75 higher for $0 drive off.
        """
        payment = base_payment
        if options_msrp > 0:
            payment += (options_msrp / 1000) * self.PAYMENT_MATH["per_1000_options"]
        if rebate_or_down > 0:
            payment -= (rebate_or_down / 1000) * self.PAYMENT_MATH["per_1000_rebate"]
        if zero_drive_off:
            payment += self.PAYMENT_MATH["zero_drive_off_multiplier"] * self.PAYMENT_MATH["per_1000_rebate"]
        return round(payment, 2)

    def format_payment_explanation(self, base: float, options: float, rebate: float) -> str:
        """Generate a clear explanation of the payment calculation."""
        payment = self.calculate_payment(base, options, rebate)
        lines = [
            f"Base payment (ad car): ${base:.0f}/mo",
        ]
        if options > 0:
            add = (options / 1000) * self.PAYMENT_MATH["per_1000_options"]
            lines.append(f"Added options (${options:.0f}): +${add:.0f}/mo (${self.PAYMENT_MATH['per_1000_options']} per $1k)")
        if rebate > 0:
            sub = (rebate / 1000) * self.PAYMENT_MATH["per_1000_rebate"]
            lines.append(f"Down payment/rebate (${rebate:.0f}): -${sub:.0f}/mo (${self.PAYMENT_MATH['per_1000_rebate']} per $1k)")
        lines.append(f"\nTotal payment: ${payment:.0f}/mo + tax")
        return "\n".join(lines)

    # ========================
    # DEAL TRACKING
    # ========================

    def create_deal(self, customer_name: str, vehicle: str = "", **kwargs: Any) -> DealRecord:
        """Create a new deal record."""
        deal_id = f"NCL{len(self.deals) + 1:04d}"
        deal = DealRecord(
            deal_id=deal_id,
            date=datetime.utcnow().strftime("%Y-%m-%d"),
            customer_name=customer_name,
            vehicle=vehicle,
            **kwargs,
        )
        self.deals[deal_id] = deal
        self._save_data()
        return deal

    def update_deal(self, deal_id: str, **kwargs: Any) -> Optional[DealRecord]:
        """Update an existing deal."""
        deal = self.deals.get(deal_id)
        if deal:
            for key, value in kwargs.items():
                if hasattr(deal, key):
                    setattr(deal, key, value)
            self._save_data()
        return deal

    def get_deal(self, deal_id: str) -> Optional[DealRecord]:
        return self.deals.get(deal_id)

    def get_active_deals(self) -> List[DealRecord]:
        """Get all non-closed, non-lost deals."""
        return [d for d in self.deals.values() if d.status not in ("closed", "lost", "paid")]

    def get_pipeline_summary(self) -> Dict[str, int]:
        """Get deal counts by status."""
        counts = {}
        for deal in self.deals.values():
            counts[deal.status] = counts.get(deal.status, 0) + 1
        return counts

    # ========================
    # DEALER MANAGEMENT
    # ========================

    def add_dealer(self, dealership: str, **kwargs: Any) -> DealerRecord:
        dealer = DealerRecord(dealership=dealership, **kwargs)
        self.dealers[dealership] = dealer
        self._save_data()
        return dealer

    def update_dealer(self, dealership: str, **kwargs: Any) -> Optional[DealerRecord]:
        dealer = self.dealers.get(dealership)
        if dealer:
            for key, value in kwargs.items():
                if hasattr(dealer, key):
                    setattr(dealer, key, value)
            dealer.last_contact = datetime.utcnow().strftime("%Y-%m-%d")
            self._save_data()
        return dealer

    def get_dealers(self) -> List[DealerRecord]:
        return list(self.dealers.values())

    # ========================
    # COMPANY INFO
    # ========================

    def set_company_info(self, **kwargs: Any) -> None:
        self.company_info.update(kwargs)
        self._save_data()

    def get_company_info(self) -> Dict[str, Any]:
        return self.company_info

    # ========================
    # FORMATTED OUTPUTS
    # ========================

    def format_script(self, script: SalesScript) -> str:
        """Format a script for display."""
        lines = [
            f"SCRIPT: {script.name}",
            f"Phase {script.phase} — {self.NCL_PHASES.get(script.phase, '')}",
            f"Tone: {script.tone}",
            "",
            script.script,
        ]
        if script.variations:
            lines.append("\nVARIATIONS:")
            for i, v in enumerate(script.variations, 1):
                lines.append(f"  {i}. {v}")
        if script.success_tips:
            lines.append("\nSUCCESS TIPS:")
            for tip in script.success_tips:
                lines.append(f"  ✓ {tip}")
        return "\n".join(lines)

    def format_objection(self, oh: ObjectionKillShot) -> str:
        """Format an objection kill shot."""
        lines = [
            f'OBJECTION: "{oh.objection}"',
            "",
            f"KILL SHOT:",
            oh.kill_shot,
        ]
        if oh.follow_up:
            lines.append(f"\nFOLLOW-UP: {oh.follow_up}")
        if oh.alternative:
            lines.append(f"\nALTERNATIVE: {oh.alternative}")
        return "\n".join(lines)

    def format_pipeline(self) -> str:
        """Format the deal pipeline."""
        if not self.deals:
            return "No deals in pipeline."

        lines = ["DEAL PIPELINE", "=" * 60]
        summary = self.get_pipeline_summary()
        for status, count in sorted(summary.items()):
            lines.append(f"  {status.upper()}: {count}")

        total_commission = sum(d.commission for d in self.deals.values() if not d.paid)
        lines.append(f"\nTotal pending commission: ${total_commission:,.0f}")
        lines.append("")

        for deal in sorted(self.deals.values(), key=lambda d: d.date, reverse=True)[:15]:
            lines.append(
                f"  [{deal.deal_id}] {deal.customer_name} — {deal.vehicle} "
                f"({deal.status}) | {deal.hot_button or 'no hot button'} | "
                f"${deal.commission:,.0f}"
            )
            if deal.next_action:
                lines.append(f"    → {deal.next_action} ({deal.next_action_date})")

        return "\n".join(lines)

    def format_phase_guide(self, phase: int) -> str:
        """Format a complete phase guide with all scripts."""
        phase_name = self.NCL_PHASES.get(phase, f"Phase {phase}")
        scripts = self.get_scripts_by_phase(phase)

        lines = [
            f"PHASE {phase}: {phase_name}",
            "=" * 60,
        ]
        for s in scripts:
            lines.append("")
            lines.append(f"--- {s.name} ---")
            lines.append(s.script)
            if s.success_tips:
                lines.append("\nTips:")
                for tip in s.success_tips:
                    lines.append(f"  ✓ {tip}")
            lines.append("")

        return "\n".join(lines)

    def format_quick_ref_card(self) -> str:
        """Format a quick reference card for the desk."""
        return (
            "┌─────────────────────────────────────────────────────────────┐\n"
            "│              NCL AUTO BROKERS — QUICK REF                  │\n"
            "├─────────────────────────────────────────────────────────────┤\n"
            "│ 3 GOLDEN RULES:                                             │\n"
            "│ 1. Stay on the f#$%ing phone                                │\n"
            "│ 2. Control the frame                                        │\n"
            "│ 3. Always Be Closing (ABC)                                  │\n"
            "├─────────────────────────────────────────────────────────────┤\n"
            "│ MATH: $20/$1k options | $30/$1k down | $75 for $0 drive off │\n"
            "├─────────────────────────────────────────────────────────────┤\n"
            "│ OBJECTION KILL SHOTS:                                       │\n"
            "│ 'Think about it' → 'What specifically?'                     │\n"
            "│ 'Ask spouse' → '3-way call now'                             │\n"
            "│ 'Check dealers' → 'I'll beat by $500 or pay you'            │\n"
            "│ 'Fee too high' → '400% ROI — you save $2,405'               │\n"
            "│ 'No credit card' → 'Secure Docusign — refundable'           │\n"
            "├─────────────────────────────────────────────────────────────┤\n"
            "│ 5 CLOSES: Assumptive | Either/Or | Take Away | Columbo      │\n"
            "│         | Write the Check                                   │\n"
            "├─────────────────────────────────────────────────────────────┤\n"
            "│ POWER PHRASES: 'When we...' not 'If you...'                 │\n"
            "│                 'We will' not 'I think we can'              │\n"
            "└─────────────────────────────────────────────────────────────┘"
        )

    def format_mirror_speech(self) -> str:
        """Format the daily mirror speech."""
        company = self.company_info.get("name", "[Company]")
        return (
            "THE MORNING WOLF RITUAL\n"
            "=" * 60 + "\n\n"
            "7:00 AM — WAKE UP. NO SNOOZE. Losers hit snooze. Wolves hunt.\n\n"
            "7:15 AM — COLD SHOWER. Discomfort is fuel.\n\n"
            "7:30 AM — REVIEW YESTERDAY'S LOSSES. Where did you choke?\n\n"
            "7:45 AM — LISTEN TO 1 CLOSING CALL from the top performer.\n\n"
            "8:00 AM — THE MIRROR SPEECH (say it OUT LOUD):\n\n"
            '"'
            "Listen to me. You are a f#$%ing monster.\n\n"
            f"Today you will talk to people.\n"
            f"Today you will close deals.\n"
            f"Today you will make commission at {company}.\n\n"
            "The customer doesn't know what they want. YOU do.\n\n"
            "When they say 'too expensive' — you show them value.\n"
            "When they say 'let me think' — you show them fear of loss.\n"
            "When they say 'I'll call you back' — you get the credit card NOW.\n\n"
            "You are not selling cars. You are selling TIME.\n"
            "You are selling PEACE. You are selling WINNING.\n\n"
            "Every 'no' gets you closer to 'yes'.\n"
            "Every hang-up builds your calluses.\n"
            "Every objection is a gift — they're TELLING you how to close them.\n\n"
            "Now get the f#$% on the phone and make it happen."
            '"\n\n'
            "[Slap both cheeks. Drink water. DIAL.]"
        )

    def format_sales_prompt(self, customer_input: str, deal_context: Optional[Dict] = None) -> str:
        """Generate a complete sales response prompt for the LLM."""
        response = ""
        oh = self.find_objection(customer_input)
        if oh:
            response = f"{oh.kill_shot}\n\n{oh.follow_up}"

        parts = []
        parts.append("You are a professional car lease salesperson at NCL Auto Brokers.")
        parts.append("Be confident, helpful, and conversational. Never sound robotic.")
        parts.append("Use the customer's name naturally. Listen more than you talk.")
        parts.append("Present deals as solutions, not transactions.")

        company = self.company_info.get("name", "NCL Auto Brokers")
        parts.append(f"Company: {company}")

        if deal_context:
            if deal_context.get("customer_name"):
                parts.append(f"Customer name: {deal_context['customer_name']}")
            if deal_context.get("budget"):
                parts.append(f"Budget: ${deal_context['budget']}/mo")
            if deal_context.get("vehicle"):
                parts.append(f"Vehicle: {deal_context['vehicle']}")
            if deal_context.get("hot_button"):
                parts.append(f"HOT BUTTON: {deal_context['hot_button']} — USE THEIR WORD")

        parts.append(f"\nCustomer said: {customer_input}")
        if response:
            parts.append(f"\nUse this kill shot: {response}")
        else:
            parts.append("\nRespond naturally. Find their hot button. Move toward the close.")

        return "\n".join(parts)
