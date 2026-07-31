import lume from "lume/mod.ts";
import theme from "theme/mod.ts";

const site = lume({
  location: new URL("https://zxczxc.dev/"),
});

site.ignore("README.md", "scripts", "notes");

// The feed plugin builds items from pre-layout content, which the theme's
// base_path plugin never processes — root-absolute references (/foo.png)
// would resolve against the origin and lose the /blog subpath. Prefix them
// here; no-op once the site moves to a root custom domain.
const prefix = site.options.location.pathname.replace(/\/+$/, "");

site.use(theme({
  // Prism bundles only markup/css/clike/javascript. Without autoload a
  // ```python fence still gets class="language-python" but no tokens at all,
  // so highlighting silently does nothing. Token colors live in _data.yml
  // (extra_head), not in a downloaded Prism theme: those are single-mode and
  // this site has a manual light/dark toggle to follow.
  prism: { autoloadLanguages: true },
  feed: {
    items: {
      image: "=image",
      content: (data) =>
        data.feedContent ??
          String(data.children).replace(/(src|href)="\/(?!\/)/g, `$1="${prefix}/`),
    },
  },
}));

export default site;
