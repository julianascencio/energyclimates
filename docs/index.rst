EnergyClimates
==============

.. raw:: html

   <div class="ec-hero">
     <div class="ec-kicker">Climate data · transparent methods · reproducible studies</div>
     <h2>Understand the climate behind your energy system.</h2>
     <p>Python tools to classify, compare and map climates for solar PV,
     PV + battery systems and standalone battery storage.</p>
     <div class="ec-creator">
       <a href="https://asvaconsulting.com"><img src="https://asvaconsulting.com/wp-content/uploads/2022/05/ASVA-1-1-scaled.jpg" alt="ASVA Consulting"></a><br>
       Created by <a href="https://asvaconsulting.com">ASVA Consulting</a> ·
       <a href="mailto:contacto@asvaconsulting.com">contacto@asvaconsulting.com</a>
     </div>
   </div>

.. grid:: 1 1 3 3
   :gutter: 3

   .. grid-item-card:: Input
      :link: inputs
      :link-type: doc

      Declare variables, units, calendars and provenance. Normalize local files
      to a monthly climate cube.

   .. grid-item-card:: Methods
      :link: methods
      :link-type: doc

      Extract climate features, apply KGPV/PVCZ, or explore experimental
      PV, hybrid, battery and ML profiles.

   .. grid-item-card:: Analysis
      :link: analysis
      :link-type: doc

      Connect data and methods in repeatable studies. Export classifications,
      maps and the evidence behind each run.

Start with the :doc:`quickstart`, explore the :doc:`auto_examples/index`,
open the :doc:`interactive atlas <atlas>`, or consult the :doc:`api`.
The installed Python package works independently of the repository's atlas assets.

.. toctree::
   :hidden:
   :maxdepth: 2

   getting-started
   user-guide
   auto_examples/index
   api
   development
   references

What is available
-----------------

* Published KGPV: six temperature/precipitation groups, four irradiation bands
  and twelve merged zones, with explicit boundary conventions.
* PVCZ map import, classification and subdaily stressor utilities.
* Experimental plain-language PV, PV + battery and battery climate profiles.
* Experimental ML groups with geographic holdout diagnostics and portable JSON models.
* Local CSV, Parquet, NetCDF, Zarr and monthly GeoTIFF adapters.
* The existing interactive atlas, including 49 bundled scientific layers.

Scientific scope
----------------

Published classifications retain their sources. New profiles and cluster models
are experimental climate screening tools, not predictions of yield, storage size,
battery safety, lifetime, cooling demand or financial return. Missing observations
remain visible. The common 1996–2022 atlas period is 27 years, not a 30-year normal.
See the :doc:`validation` record and :doc:`ATLAS_REFERENCE` for evidence and limits.

Code, documentation and examples are developed with AI assistance under developer
direction using identified literature and datasets. Validation is evolving and
errors may remain; verify the cited assumptions and results for your intended use.

Related projects: `OrbitalPV <https://julianascencio.github.io/orbital-pv/>`_ and
`Energy Data Insights <https://julianascencio.github.io/energy-data-insights/>`_.
This site follows their Sphinx/PyData documentation format.
