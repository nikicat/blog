# How to make personal blog on Github Pages (with Google Analytics)

Create regular Github Pages repo, then edit `_config.yaml`:
```
google_analytics: G-XXX # https://support.google.com/analytics/answer/9306384
remote_theme: jekyll/minima
plugins:
- jekyll-remote-theme
minima:
  skin: dark
```

Thanks to https://github.com/jekyll/minima/issues/561#issuecomment-748793956
