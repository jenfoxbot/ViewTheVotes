# Engagement Features Plan

## Goal
Make congressional vote data more engaging by helping people understand WHY they should care about what their elected officials are voting for.

## Selected Features (Priority Order)

### 1. ⭐ Shareable Cards (CURRENT - `feature/shareable-cards`)
**Status**: In Progress

Single-stat social media graphics:
- "217 reps voted to [simple action]. Was yours one of them?"
- Clean, bold design optimized for sharing
- QR code or link to look up your representative's vote

**Implementation**:
- New image generator in `scripts/` 
- Uses existing vote count data from `vote_*.json`
- Output: `03_shareable.png` in social_media folder

---

### 2. Impact Headlines (`feature/impact-headlines`)
**Status**: Not Started

Lead with personal impact instead of bill titles:
- "This vote could raise your grocery prices"
- "Your kids' school funding depends on this"
- "This affects your health insurance premiums"

**Implementation**:
- Modify `simplify_to_eli5()` to generate punchy headlines
- Add `impact_headline` field to analysis output

---

### 3. Before/After Framing (`feature/before-after-framing`)
**Status**: Not Started

Concrete examples of what happens:
- "If this passes: [concrete example]"
- "If this fails: [concrete example]"

**Implementation**:
- New section in analysis output
- Template-based generation from bill category

---

### 4. Audience Sections (`feature/audience-sections`)
**Status**: Not Started

Targeted callouts for different groups:
- **Parents**: School/childcare impacts
- **Workers**: Job protection changes
- **Homeowners/Renters**: Housing cost impacts
- **Retirees**: Medicare/Social Security effects

**Implementation**:
- Generate multiple audience-specific summaries per bill
- New image template with audience tabs

---

### 5. Accountability Tracking (`feature/accountability-tracking`)
**Status**: Not Started

Compare votes to campaign promises:
- "Your rep said X, then voted Y"
- Side-by-side comparisons with neighboring districts

**Implementation**:
- Requires external data source for campaign positions
- Database of representative statements/positions

---

### 6. Local Connection (`feature/local-connection`)
**Status**: Not Started

Connect votes to local impact:
- "3 companies in [your state] would be affected"
- "Your district received $X in funding from this program"
- Map overlays showing where impacts hit hardest

**Implementation**:
- Requires external data (state funding, local businesses)
- Geographic data integration
- Most complex feature

---

## Progress Tracking

| Feature | Branch | Status | Notes |
|---------|--------|--------|-------|
| Shareable Cards | `feature/shareable-cards` | 🟡 In Progress | Starting now |
| Impact Headlines | `feature/impact-headlines` | ⬜ Not Started | |
| Before/After | `feature/before-after-framing` | ⬜ Not Started | |
| Audience Sections | `feature/audience-sections` | ⬜ Not Started | |
| Accountability | `feature/accountability-tracking` | ⬜ Not Started | Needs external data |
| Local Connection | `feature/local-connection` | ⬜ Not Started | Most complex |

---

*Created: February 21, 2026*
