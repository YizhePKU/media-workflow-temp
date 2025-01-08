Extract detailed descriptions from the image according to some predefined aspects.
The output should be a JSON object with the following keys:

- usage
- mood
- color_scheme
- culture_traits
- industry_domain
- seasonality
- holiday_theme

Each value should be a long, complete sentence that describes the image in detail.
If no relevant information can be extracted from the image, or if the result is vague, set the value to null instead.
