# codameter build entrypoints.
#
# The Quarto site and the paper are rendered LOCALLY and the outputs committed:
# CI (.github/workflows/quarto.yml) only *publishes* quarto/_site, it does not
# render. So after editing any .qmd, rebuild and commit the outputs.
#
#   make paper   # paper/manuscript.qmd -> manuscript.tex + manuscript.pdf
#   make site    # quarto/*.qmd -> quarto/_site (+ _freeze), executes notebooks
#   make all     # both
#   make check   # fast: warn if outputs are stale vs their .qmd sources (no render)
#
# Rendering executes live notebook cells through the pixi kernel (needs disba),
# so it takes minutes — run it deliberately, not on every commit.

# Quarto must see the pixi Python so the codameter-pixi kernel resolves.
export QUARTO_PYTHON := $(CURDIR)/.pixi/envs/default/bin/python

.PHONY: all paper site figs check clean

all: figs paper site

# Regenerate the demo figures (uses matplotlib style in codameter.synthetic_demo).
# Must run in the pixi env so the deps and the Optima font stack resolve.
figs:
	pixi run python literature/synthetic_dvv_demo.py

# Build the paper. Run under pixi so build.py's figure subprocess (sys.executable)
# is the pixi python, not a bare/base python that lacks the deps.
paper:
	pixi run python paper/build.py

site:
	pixi run quarto render quarto/

# Non-rendering guard: exit non-zero if a rendered output is older than its
# source, so you get a reminder to `make paper` / `make site` before committing.
check:
	@stale=0; \
	if [ paper/manuscript.qmd -nt paper/manuscript.tex ]; then \
	  echo "stale: paper/manuscript.tex older than manuscript.qmd -> make paper"; stale=1; fi; \
	newest_qmd=$$(ls -t quarto/*.qmd | head -1); \
	if [ "$$newest_qmd" -nt quarto/_site/index.html ]; then \
	  echo "stale: quarto/_site older than $$newest_qmd -> make site"; stale=1; fi; \
	if [ $$stale -eq 0 ]; then echo "outputs up to date"; fi; \
	exit $$stale
