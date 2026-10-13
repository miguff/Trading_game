# Feature Specification: Mobile-Responsive Player UI

**Feature Branch**: `feature/module_D_mobile_ui`

**Created**: 2026-06-11

**Status**: Draft

**Input**: User description: "Ensure the game is fully playable on a mobile phone screen, allowing players to use their own devices instead of a laptop."

## Scope

### In Scope
- Join screen (player name entry and role assignment display)
- Trading screen (live prices, buy/sell controls, position and P&L display, price charts)
- Round summary and leaderboard screen (round P&L, cumulative P&L, player rankings)
- Touch-friendly sizing and spacing for all interactive elements on player-facing screens
- Responsive layout adaptation for small viewports
- Admin screen (game master controls)


### Out of Scope
- Any backend API changes
- Any game logic or trading rule changes
- Native mobile app development

## Assumptions
- Primary target orientation is portrait on modern smartphones.
- Players use contemporary mobile browsers with standard CSS support.
- The minimum supported viewport width is 390px (representative of common smartphones).
- No hardware-specific features (camera, GPS, etc.) are required.
- Desktop layout should remain visually similar and functionally equivalent to the current layout; minor spacing or sizing adjustments are acceptable as a side effect of the mobile-first CSS approach.
- The mobile layout stretches fluidly from 390px up to 767px; the desktop layout activates at 768px and above. No dedicated tablet breakpoint is required.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Player joins the game on a mobile phone (Priority: P1)
A player can open the game URL on their smartphone, enter their name, and join the session without horizontal scrolling or zooming.

**Why this priority**: The join screen is the first interaction every player has with the game. If it does not work on mobile, players cannot enter the game at all.

**Independent Test**: Open the join screen on a 390px wide viewport, enter a name, and verify the entire flow fits within the screen width and all elements are reachable.

**Acceptance Scenarios**:
1. **Given** a player opens the game on a mobile device, **when** they view the join screen, **then** all content fits within the viewport width without horizontal scrolling.
2. **Given** a player is on the join screen, **when** they tap the name input field, **then** the field is large enough for comfortable text entry and the on-screen keyboard does not obscure critical elements.
3. **Given** a player has entered their name, **when** they tap the join button, **then** the button is large enough to be tapped reliably without mis-taps.

---

### User Story 2 - Player trades during an active round on a mobile phone (Priority: P1)
A player can view live prices, place buy and sell orders, and monitor their position and P&L on a smartphone screen.

**Why this priority**: Trading is the core gameplay loop. The trading screen must be fully functional on mobile for the game to be playable without laptops.

**Independent Test**: During an active round on a 390px wide viewport, verify that prices, charts, controls, and P&L information are all visible and interactive without horizontal scrolling.

**Acceptance Scenarios**:
1. **Given** an active round on a mobile device, **when** the player views the trading screen, **then** all critical information (current price, position, P&L, buy/sell buttons) is visible without horizontal scrolling.
2. **Given** a player on the trading screen, **when** they tap buy or sell, **then** the buttons are large enough for reliable touch interaction and provide clear visual feedback.
3. **Given** a player on the trading screen, **when** they view the price chart, **then** the chart container fits within the viewport without breaking the layout, and the chart is horizontally scrollable to preserve full detail.

---

### User Story 3 - Player views round summary and leaderboard on a mobile phone (Priority: P1)
After a round ends, a player can view their round P&L, cumulative P&L, and the leaderboard on a smartphone screen.

**Why this priority**: The summary and leaderboard provide the competitive feedback loop. Players must be able to see results clearly on their own devices.

**Independent Test**: After a round ends on a 390px wide viewport, verify that the summary and leaderboard are fully visible and readable without horizontal scrolling.

**Acceptance Scenarios**:
1. **Given** a round has ended on a mobile device, **when** the summary screen is displayed, **then** all player results and rankings fit within the viewport without horizontal scrolling.
2. **Given** a player views the leaderboard, **when** there are many players, **then** the list is scrollable vertically and remains readable without horizontal scrolling.

---

### User Story 4 - Player interacts with touch-optimized controls (Priority: P2)
All interactive elements on player-facing screens are sized and spaced appropriately for finger-based touch interaction.

**Why this priority**: Touch optimization reduces mis-taps and frustration, improving the overall mobile experience.

**Independent Test**: Verify on a touch device that all buttons, inputs, and interactive elements can be activated reliably without accidental adjacent activations.

**Acceptance Scenarios**:
1. **Given** a player on any player-facing screen, **when** they attempt to tap any button or input, **then** the target is large enough and sufficiently spaced from other targets to prevent mis-taps.
2. **Given** a player taps an interactive element, **then** the element provides immediate visual feedback confirming the interaction.

---

### User Story 5 - Game master uses admin controls on a mobile phone (Priority: P2)
The game master can view player status, select price scenarios, start rounds, and end the game from a smartphone screen.

**Why this priority**: While the game master may prefer a laptop, supporting mobile admin controls ensures the game can be run entirely from mobile devices if needed.

**Independent Test**: Open the admin screen on a 390px wide viewport and verify that all controls (scenario selection, round start, player list) are reachable and functional without horizontal scrolling.

**Acceptance Scenarios**:
1. **Given** a game master opens the admin screen on a mobile device, **when** they view the controls, **then** all admin functions are accessible without horizontal scrolling.
2. **Given** a game master on the admin screen, **when** they view the player list, **then** the list is displayed as vertically stacked cards, one per player, without horizontal scrolling.
3. **Given** a game master on the admin screen, **when** they interact with complex controls (e.g., scenario dropdown, player list), **then** the controls are vertically stacked and scrollable as needed.
4. **Given** a game master on the admin screen, **when** they tap any button or control, **then** the touch target meets the same 48×48 CSS pixel minimum as player-facing screens.

### Edge Cases
- What happens when a player rotates their device to landscape orientation? A polite "Please rotate to portrait for the best experience" overlay is displayed. The game remains functional underneath, but landscape is not an optimized layout.
- How does the interface behave on very small viewports below 390px? The layout SHOULD degrade gracefully, but 390px is the minimum guaranteed supported width.
- What happens when the on-screen keyboard appears? Critical controls and information MUST remain accessible or scrollable into view.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The join screen MUST be fully usable on a viewport width of 390px without horizontal scrolling.
- **FR-002**: The trading screen MUST be fully usable on a viewport width of 390px without horizontal scrolling.
- **FR-003**: The round summary and leaderboard screen MUST be fully usable on a viewport width of 390px without horizontal scrolling.
- **FR-004**: All interactive elements on player-facing screens (buttons, inputs, selectable items) MUST have a minimum touch target size of 48×48 CSS pixels, with at least 8px spacing between adjacent targets, to ensure reliable touch interaction on a mobile device.
- **FR-005**: Text and numerical data on player-facing screens MUST remain readable without requiring zoom on a 390px wide viewport.
- **FR-006**: The layout of player-facing screens MUST adapt to the available viewport width without hiding or breaking functionality.
- **FR-007**: Price charts on the trading screen MUST remain visible and readable on a 390px wide viewport. Charts MUST be horizontally scrollable within their container to preserve full detail without causing page-level horizontal scrolling.
- **FR-008**: When the on-screen keyboard appears (e.g., on name entry), the active input and related controls MUST remain accessible.
- **FR-009**: On the trading screen, buy and sell buttons MUST be arranged side-by-side with equal width on mobile viewports, maintaining a horizontal layout.
- **FR-010**: The admin screen MUST be fully usable on a viewport width of 390px without horizontal scrolling. Complex controls MAY be vertically stacked and scrollable.

## Success Criteria

- Players can complete the full join-to-trading-to-leaderboard flow on a mobile device without horizontal scrolling.
- All player-facing screens render correctly and are fully functional on a viewport width of 390px.
- Touch targets on player-facing screens meet minimum size guidelines for reliable finger interaction.
- Text and data remain legible without zooming on a smartphone screen.
- The game is playable by players using only their own mobile devices, with no laptop required.
- The admin screen is functional on a mobile device, allowing the game master to run the game from a phone if needed.

## Clarifications

### Session 2026-06-11
- Q: Should responsive styles be added to the existing `styles.css` or created as a separate CSS file? → A: Add responsive breakpoints directly into the existing `styles.css` using `@media` queries.
- Q: What is the minimum touch target size for interactive elements on mobile? → A: 48×48 CSS pixels minimum per target, with at least 8px spacing between adjacent targets.
- Q: How should price charts behave on a 390px viewport where 120 candles may not fit? → A: Charts become horizontally scrollable within their container to preserve full detail and prevent layout overflow.
- Q: How should buy and sell buttons be arranged on the mobile trading screen? → A: Side-by-side with equal width, maintaining a horizontal layout.
- Q: What should happen when a player rotates their device to landscape orientation? → A: Show a polite "Please rotate to portrait for the best experience" overlay; the game remains functional underneath but is not optimized for landscape.
- Q: What mobile viewport standard should the admin screen meet? → A: Admin screen must be usable on 390px, but complex controls may be vertically stacked and scrollable.
- Q: How should the admin player list be presented on a 390px viewport? → A: Convert to a vertically stacked card layout, one card per player.
- Q: Should the CSS approach be mobile-first or desktop-first? → A: Mobile-first: base styles target 390px and smaller, with `@media (min-width: 768px)` for tablet/desktop enhancements.
- Q: Should the desktop layout remain identical to the current layout after mobile-first CSS changes? → A: Desktop layout should remain visually similar and functionally equivalent; minor spacing/sizing adjustments are acceptable.
- Q: How should intermediate viewports (500px–767px) be handled? → A: Mobile layout stretches fluidly from 390px to 767px; desktop layout activates at 768px and above.

## Dependencies

- Existing player-facing screens (join, trading, leaderboard) from the Energy Trading Game MVP.
- No backend or game logic changes are required for this feature.
- CSS changes are confined to the existing `styles.css` file using a mobile-first approach: base styles target 390px and smaller, with `@media (min-width: 768px)` for tablet/desktop enhancements. No separate CSS file is introduced.
