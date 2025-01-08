Extract tags from the image according to some predefined aspects.

The output should be a JSON object with the following keys:
- theme_identification: summarize the core theme of the material, such as education, technology, health, etc.
- emotion_capture: summarize the emotional tone conveyed by the material, such as motivational, joyful, sad, etc.
- style_annotation: summarize the visual or linguistic style of the material, such as modern, vintage, minimalist, etc.
- color_analysis: summarize the main colors of the material, such as blue, red, black and white, etc.
- scene_description: summarize the environmental background where the material takes place, such as office, outdoor, home, etc.
- character_analysis: summarize characters in the material based on their roles or features, such as professionals, children, athletes, etc.
- purpose_clarification: summarize the intended application scenarios of the material, such as advertising, education, social media, etc.
- technology_identification: summarize the specific technologies applied in the material, such as 3D printing, virtual reality, etc.
- time_marking: summarize time tags based on the material's relevance to time, if applicable, such as spring, night, 20th century, etc.
- trend_tracking: summarize current trends or hot issues, such as sustainable development, artificial intelligence, etc.

Each tag value should be a JSON list containing zero of more short strings. Each string should briefly describes the
image. Only use strings inside lists, not complex objects.

If the extracted value is vague or non-informative, or if the tag doesn't apply to this image, set the value to an empty list instead.
If the extracted value is a complex object instead of a string, summarize it in a short string instead.
If the extracted value is too long, shorten it by summarizing the key information.
