# website

Source code for [ogu.nz](https://ogu.nz), a static site generator built with Python, HTML, SCSS, and JavaScript. Infrastructure managed with Terraform.

## Features

- Static site generation with Markdown support.
- Article and tag management.
- Customizable templates and styles.
- SEO-friendly with sitemaps and RSS feeds.

## Installation

1. Clone the repository:
   ```sh
   git clone https://github.com/tetsuo/website.git
   ```
2. Install dependencies:
   ```sh
   pip install -r requirements.txt
   npm install
   ```

## Usage

- Generate favicons:
  ```sh
  convert -size 2049x2049 "xc:rgba(0,0,0,0)" -set colorspace RGB \
  -fill '#fff' -stroke '#0000ff' -strokewidth 300 -draw 'circle 1024,1024 1024,153' \
  -fill 'black' -stroke '#1ba9e4' -strokewidth 290 -draw 'circle 1024,1024 760,760' \
  -alpha set -background none \
  -wave 100x1900 \
  -colorspace sRGB \
  -distort SRT 8 \
  tmp/circle_sRGB.png && \
  ./generate-favicons.js tmp/circle_sRGB.png
  ```
- Build pages:
  ```sh
  python generate.py
  ```
- Build styles:
  ```sh
  npm run sass
  ```
- Upload to S3 using the provided sync script:
  ```sh
  PUBLIC_S3_BUCKET_NAME="somebucket" \
  DOMAIN_NAME="example.com" \
  YES=1 \
  ./sync-public-bucket .
  ```

## License

MIT License. See [LICENSE](LICENSE) for details.
