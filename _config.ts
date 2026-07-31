import lume from "lume/mod.ts";
import theme from "theme/mod.ts";

// Prism bundles only markup/css/clike/javascript; every other fence renders
// with a language-* class and no tokens at all. Load the grammars this blog
// actually uses, explicitly. (`autoloadLanguages` fetches them asynchronously,
// which loses the race in a cold one-shot build: the dev server highlights
// after its second pass, CI never gets one, and the deploy silently ships
// unhighlighted code.) `console` and `sh` are aliases Prism maps to bash.
import "npm:prismjs@1.30.0/components/prism-python.js";
import "npm:prismjs@1.30.0/components/prism-bash.js";
import "npm:prismjs@1.30.0/components/prism-ini.js";
import "npm:prismjs@1.30.0/components/prism-yaml.js";
import "npm:prismjs@1.30.0/components/prism-json.js";
import "npm:prismjs@1.30.0/components/prism-typescript.js";
import "npm:prismjs@1.30.0/components/prism-shell-session.js";
import Prism from "npm:prismjs@1.30.0";

// GitHub and dev.to spell it ```console; Prism only knows shell-session.
Prism.languages.console = Prism.languages["shell-session"];

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
  // Token colors live in _data.yml (extra_head), not in a downloaded Prism
  // theme: those are single-mode and this site has a manual light/dark toggle
  // to follow.
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
