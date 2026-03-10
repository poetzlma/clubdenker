What to Check (Design-wise & Best Practices)
When auditing the current codebase, the agent should check for the following:
Arbitrary Sizing and Spacing: Replace manual pixel values (like 13px or 125px) with a constrained spacing and sizing system
. A common best practice is using a base of 16px and building a scale where adjacent values are at least 25% apart so the difference is perceivable
.
Color Bloat: Check for a high volume of slightly different hex codes. Refactor these into a palette of 8–10 shades per color (grey, primary, and accents like red for destructive actions or green for positive trends)
.
Visual Hierarchy: Ensure that importance is communicated through font weight and color contrast rather than just size
. For instance, de-emphasize secondary content by using a softer grey rather than a tiny font size
.
Typography Consistency: Audit all text elements. Instead of picking font sizes on the fly, the agent should use a restrictive type scale (e.g., 12px, 14px, 16px, 18px, 20px, 24px, 30px)
.
Accessibility: Verify that all normal text has a contrast ratio of at least 4.5:1 and that icons or labels support information that would otherwise rely on color alone
.
Central Management for Maintainability
To make the project maintainable, you must centrally manage Design Tokens. These are repeating decisions that should be defined in a single location (like a theme file or CSS variables)
:
Typography: Font families, weight scales, and line heights
.
Spacing: Margins, padding, and fixed widths for elements like sidebars
.
Elevation: A fixed set of about five shadows to position elements on a virtual z-axis
.
Global Elements: Centrally manage your comprehensive color palette and border radii to ensure a consistent personality across the app
.
Recurring and Reusable Components
Organize components using the Atomic Design methodology, which breaks the UI into five distinct levels
:
Atoms: The smallest units, such as buttons (primary/secondary/tertiary), inputs, checkboxes, and icons
.
Molecules: Simple groups of atoms, like a form group (label + input) or a search bar
.
Organisms: Complex UI sections, such as a navigation bar, sidebar, or product card
.
Templates and Pages: High-level layouts that arrange organisms into a functional screen
.
How to Store Components in the Project
Atomic Structure: Store components in folders corresponding to their Atomic level (/components/atoms, /components/organisms, etc.)
.
Separation of Concerns: Keep component logic and styles together but separate from the Global Design System (the tokens mentioned above)
.
Feature-First Implementation: During refactoring, encourage the agent to focus on actual functionality (e.g., a "search flight" component) rather than the "application shell" or navigation
.
Units: Use px or rem units for font sizes in your system rather than em units to ensure computed sizes remain predictable across nested components
.