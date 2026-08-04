# Load-case diagnostics note

## Summary

The recent stress mismatch is now most likely a load-case-definition issue rather than a solver stability issue.

## What was tested

1. Support sensitivity check:
- Tightening or fixing supports changed compression only marginally in the original setup.
- This indicated support compliance was not the primary source of low compression.

2. Pressure activation checks in the original setup:
- Increasing pressure magnitudes produced little to no stress response change.
- Zero-pressure runs were near-identical to baseline.
- This showed the previous pressure keywords were effectively inert for the intended structural traction loading.

3. Active traction reformulation:
- Switching to explicit normal traction made water loading strongly active.
- Compression increased substantially, but principal tension also overshot.

4. Sign and direction experiments:
- Load sign flips and radial projection variants changed the balance but did not produce a physically consistent benchmark match.
- Cases either retained high tension or over-compressed in unrealistic combinations.

5. Load sweep behavior:
- Scaling upstream/downstream heads could tune compression near target.
- The same cases then drove tension far above acceptable range.

## Engineering interpretation

The mismatch pattern is not consistent with a single scalar calibration parameter.
A model can be tuned to one target metric (compression), but the coupled response (tension) becomes non-credible.
This points to load-case definition details as the dominant unresolved factor:

- exact boundary traction type and sign convention
- waterline datum versus mesh elevation datum
- pressure application region and truncation logic
- crest load representation and decomposition
- support idealization coupling with load direction

## Immediate recommendation

Use a dedicated calibration workflow that toggles each load block independently and records stress outcomes per case. Keep the production baseline SIF untouched while iterating.

## Important sanity check retained

`Data/Env_Boundaries_And_Loads.json` lists peak water pressure as 284490 Pa (rho*g*h with h=29 m). The active hydrostatic expression depends on local Z (`Coordinate 3`) and mesh datum. If the wetted boundary does not include Z=0, the model never reaches 284490 Pa even when the 29 m head is specified.
