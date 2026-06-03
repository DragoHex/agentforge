You have been improving your agent by tweaking its system prompt by hand. That is gradient descent without a learning rate.

SkillOpt treats the skill document itself as a trainable weight. A frozen GPT-5.5 goes from 41.8% to 80.7% on a hard spreadsheet benchmark, using a text file under 2,000 tokens. No fine-tuning. No bigger model.

The mechanism: a feedback loop with bounded edits, a held-out validation gate, and rollback buffers that reject bad updates. Each epoch makes small, committed changes. The skill cannot overwrite core knowledge to fix one failure.

The sharpest result is what happens when you transfer the trained skill to a different model entirely. It keeps working.

![Caption](linkedin-visuals/main-benchmarks.png)

How would you apply a structured optimization loop to a non-deterministic task, like content writing?

For a deeper dive, the full breakdown is on Substack: [<!-- SUBSTACK_URL -->]

#AgentSystems #LLM #MachineLearning #SkillOpt