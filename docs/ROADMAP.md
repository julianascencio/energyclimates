# Roadmap

This is an initial public research release. The roadmap is a set of proposed
work items, not a claim that the following capabilities already exist.

## First: establish scientific validity

- Validate PV profiles against independent, documented measured or simulated yield.
- Validate hybrid profiles against hourly PV/load/dispatch studies.
- Validate battery profiles against cell temperature, HVAC energy and ageing
  simulations or measurements across chemistries and operating strategies.
- Review threshold sensitivity, spatial transfer and the useful number of ML groups.
- Resolve the suspected label ordering in the original KGPV data with its authors.

## Data and reproducibility

- Complete the 1996–2025 common period using the remaining ERA5 inputs.
- Add provider refresh checks and reproducible dataset releases.
- Obtain the actual geographic assignments for the cited published ML maps.
- Improve memory use for very large gridded climatologies and station archives.

## Broader energy coverage

- Define and validate a wind-oriented climate classification with appropriate
  hub-height wind, variability and environmental stress features.
- Explore humidity, snow, dust, soiling, extremes and subdaily variability as
  additional PV/storage stress dimensions when adequate inputs exist.
- Keep stable published methods available beside each experimental version.

## Accessibility

- More plain-language explanations, sample datasets and contribution examples.
- A public package release after the initial API and data packaging review.
- More direct links between a climate label, its source variables and the
  energy-system decision it can actually support.
