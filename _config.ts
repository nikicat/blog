import lume from "lume/mod.ts";
import theme from "theme/mod.ts";

// TODO: switch to the custom domain once decided — canonical URLs on
// dev.to/Medium will point wherever this was at publish time.
const site = lume({
  location: new URL("https://nikicat.github.io/blog/"),
});

// The feed plugin builds items from pre-layout content, which the theme's
// base_path plugin never processes — root-absolute references (/foo.png)
// would resolve against the origin and lose the /blog subpath. Prefix them
// here; no-op once the site moves to a root custom domain.
const prefix = site.options.location.pathname.replace(/\/+$/, "");

site.use(theme({
  feed: {
    items: {
      content: (data) =>
        String(data.children).replace(/(src|href)="\/(?!\/)/g, `$1="${prefix}/`),
    },
  },
}));

export default site;
