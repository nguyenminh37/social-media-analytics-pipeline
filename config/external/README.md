# External Text Resources

## vietnamese-stopwords.txt

- Source: https://github.com/stopwords/vietnamese-stopwords
- Pinned commit: `a453d389e1b52e20748ca83ddd8b0faebb04f5aa`
- License: MIT
- Copyright: Copyright (c) 2015 Van-Duyet Le

The public stopword list is used as the baseline Vietnamese dictionary for
topic extraction. Project-specific RSS, URL, source-brand, and ASCII fallback
filters stay in `config/public_content_text_filters.json` as supplemental
pipeline filters.

MIT license notice from the upstream project:

```text
MIT License

Copyright (c) 2015 Van-Duyet Le

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
```

## VnEmoLex.xlsx and vnemolex_sentiment.json

- Source: https://zenodo.org/records/801610
- DOI: `10.5281/zenodo.801610`
- License: Creative Commons Attribution 4.0 International
- Creator: KTLab
- Published: 2017-06-01

`VnEmoLex.xlsx` is the upstream Vietnamese emotion lexicon. The runtime file
`vnemolex_sentiment.json` is generated from the XLSX source with:

```bash
python3 scripts/build_vnemolex_sentiment_lexicon.py
```

The generated JSON keeps the Vietnamese term tokens plus the upstream
`Positive` and `Negative` polarity columns. The sentiment enricher uses this
lexicon as the default local provider so demo scoring does not depend on Gemini
quota.
