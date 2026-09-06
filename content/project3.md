**Project: **

**Template reference:**

I don't know, but in principle, you can make different theme colors and templates.



With the rapid advancement of telescope technologies and the accumulation of observational data, astronomy is entering an era of unprecedented depth and breadth in data, continuously reshaping our understanding of galaxy evolution. A key challenge is how to make the most of these vast datasets from the latest deep-field surveys to reconstruct our universe—especially the properties of galaxies—in a more complete and accurate way. 

Motivated by this, we leveraged **cutting-edge observations from JWST** and applied **machine learning techniques** to classify observed galaxies, thereby constructing a comprehensive galaxy sample. We further explored how such an approach can enhance **galaxy parameter estimation**, **guide observational strategies**, and ultimately improve our understanding of galaxy formation and evolution.



## 「1」SHAPE: SOM-SED Hybrid Approach for Efficient Parameter Estimation Leveraging JWST Observation

Cover: `assets/images/research/shape1.webp`

https://ui.adsabs.harvard.edu/abs/2026A%26A...706A.277W/abstract

With the launch and application of next-generation ground- and space-based telescopes, astronomy has entered the era of big data, necessitating more efficient and robust data analysis methods. The high-quality observations provided by JWST offer a valuable opportunity to calibrate and enhance the performance of the upcoming surveys, e.g. the CSST and Euclid. In this work, we introduce a new approach (SHAPE, SOM-SED Hybrid Approach for efficient Parameter Estimation) to efficiently and accurately estimate key galaxy parameters, such as stellar mass and star formation rate (SFR), leveraging the largest and deepest JWST/NIRCam and MIRI surveys (PRIMER). As a test of methodology, we focus on galaxies at z ∼ 1.5 − 2.5. To mitigate discrepancies between input colors and the training set, we replace the default SOM weights with stacked SEDs from each cell, extending the applicability of our model to other photometric catalogs (e.g. COSMOS2020). By incorporating an SED library (SED Lib), we apply this JWST-calibrated model to the COSMOS2020 catalog. Despite the limited sample size and potential template-related uncertainties, SOM-derived estimates exhibit strong agreement with results from SED fitting using extended photometry. Under identical photometric constraints, our method outperforms traditional SED fitting techniques in SFR estimation. With its high computational efficiency, this JWST-calibrated estimator holds significant promise for next-generation large-area surveys.

Data: http://www.taoofcosmos.space/ultimate/
