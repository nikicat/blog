---
title: How to make a personal blog on GitHub Pages (with Google Analytics)
date: 2022-05-09
author: Nikolay Bryskin
tags:
  - jekyll
  - github-pages
---

Create regular Github Pages repo, then edit `_config.yaml`:

```yaml
google_analytics: G-XXX # https://support.google.com/analytics/answer/9306384
remote_theme: jekyll/minima
plugins:
- jekyll-remote-theme
minima:
  skin: dark
```

<!--more-->

Thanks to https://github.com/jekyll/minima/issues/561#issuecomment-748793956
