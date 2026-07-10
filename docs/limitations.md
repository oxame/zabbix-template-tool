# Current limitations

The LLD move engine preserves dependencies embedded inside a discovery rule. It does not yet copy
objects located elsewhere in the template export, including:

- template-level macros;
- value maps;
- master items referenced by dependent item prototypes;
- template-level dashboards or graphs referencing moved prototypes;
- linked templates.

The next milestone will identify these external references and report them before a move.
