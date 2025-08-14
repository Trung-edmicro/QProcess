ARRAY_BASED_SCHEMA={
  "type": "object",
  "description": "Schema for quiz questions, supporting both standalone questions and groups of questions under a common learning material.",
  "properties": {
    "questions": {
      "type": "array",
      "description": "Array containing standalone questions or groups of questions with shared learning material.",
      "items": {
        "type": "object",
        "description": "An item in the array, which can be a learning material group (isHL=true) or a standalone question (isHL=false).",
        "properties": {
          "isHL": {
            "type": "boolean",
            "description": "Required. Defines the structure of this item. \n- `true`: This is a LEARNING MATERIAL GROUP. Use when there is a shared context (e.g., a passage, table, or a 'Read the following...' prompt), followed by MULTIPLE complete, individually numbered questions (Question 1, Question 2,...) that refer to that context. \n- `false`: This is a STANDALONE QUESTION. Use for a single question, including 'compound questions' that have one main prompt and multiple sub-parts (a, b, c, d). The entire compound structure is treated as a SINGLE question."
          },
          "content": {
            "type": "string",
            "description": "Content. If isHL=true, this is the HTML content of the shared learning material. If isHL=false, this is the HTML content of the standalone question."
          },
          "data": {
            "type": "array",
            "description": "Array of child questions belonging to this learning material (only applies when isHL=true) often follow after the learning material. ",
            "items": {
              "type": "object",
              "description": "Schema for a child question within the learning material group.",
              "properties": {
                "content": {
                  "type": "string",
                  "description": "HTML content of the question"
                },
                "explainQuestion": {
                  "type": "string",
                  "description": "HTML explanation for the question"
                },
                "index": {
                  "type": "integer",
                  "description": "Index of the question within the 'data' array.",
                  "minimum": 0
                },
                "numberId": {
                  "type": "integer",
                  "description": "Question number identifier",
                  "minimum": 1
                },
                "indexPart": {
                  "type": "integer",
                  "description": "Index of the question part",
                  "minimum": 0
                },
                "isExplain": {
                  "type": "boolean",
                  "description": "Whether explanation is shown"
                },
                "mappingScore": {
                  "type": "object",
                  "description": "Mapping of scores for different criteria"
                },
                "optionAnswer": {
                  "type": "array",
                  "description": "Array of correct answer option indices, it can be array of correct answers ex [True,False,True,False] or [12.03,55.43,..]... ",
                  "items": {}
                },
                "scores": {
                  "type": "number",
                  "description": "Score value for the question",
                  "minimum": 0
                },
                "totalOption": {
                  "type": "integer",
                  "description": "Total number of options",
                  "minimum": 1
                },
                "typeAnswer": {
                  "type": "string",
                  "description": "Type of answer: 0=Multiple choice single answer, 1=Multiple choice multiple answers , 2=Fill-in-the-blank essay, 3=Essay, 4=Essay single answer, 5=Essay multiple answers with order, 999=Undefined",
                  "enum": ["0", "1", "2", "3", "4", "5", "999"]
                },
                "options": {
                  "type": "array",
                  "description": "Array of answer options",
                  "items": {
                    "type": "object",
                    "properties": {
                      "content": {
                        "type": "string",
                        "description": "Content of the option"
                      },
                      "isAnswer": {
                        "type": "boolean",
                        "description": "Whether this option is correct"
                      },
                      "optionLabel": {
                        "type": "string",
                        "description": "Label for the option (A, B, C, D, etc.)",
                        "pattern": "^[A-Z]$"
                      },
                      "index": {
                        "type": "integer",
                        "description": "Index of the option",
                        "minimum": 0
                      }
                    },
                    "required": [
                      "content",
                      # "isAnswer",
                      # "optionLabel",
                      "index"
                    ]
                  },
                  "minItems": 1
                }
              },
              "required": [
                "content",
                "index",
                "numberId",
                "indexPart",
                # "isExplain",
                # "mappingScore",
                # "scores",
                "typeAnswer",
                # "options"
              ]
            }
          },
          
          "explainQuestion": {
            "type": "string",
            "description": "HTML explanation for the question (only applies when isHL=false)."
          },
          "index": {
            "type": "integer",
            "description": "Index of the question/group in the main 'questions' array.",
            "minimum": 0
          },
          "numberId": {
            "type": "integer",
            "description": "Question number identifier (only applies when isHL=false).",
            "minimum": 1
          },
          "indexPart": {
            "type": "integer",
            "description": "Index of the question part (only applies when isHL=false).",
            "minimum": 0
          },
          "isExplain": {
            "type": "boolean",
            "description": "Whether explanation is shown (only applies when isHL=false)."
          },
          "mappingScore": {
            "type": "object",
            "description": "Mapping of scores for different criteria (only applies when isHL=false)."
          },
          "optionAnswer": {
            "type": "array",
            "description": "Array of correct answer option indices, it can be array of correct answers ex [True,False,True,False] or [12.03,55.43,..]... (only applies when isHL=false).",
            "items": {}
          },
          "scores": {
            "type": "number",
            "description": "Score value for the question (only applies when isHL=false).",
            "minimum": 0
          },
          "totalOption": {
            "type": "integer",
            "description": "Total number of options (only applies when isHL=false).",
            "minimum": 1
          },
          "typeAnswer": {
            "type": "string",
            "description": "Type of answer: 0=Multiple choice single answer, 1=Multiple choice multiple answers , 2=Fill-in-the-blank essay, 3=Essay, 4=Essay single answer, 5=Essay multiple answers with order, 999=Undefined (only applies when isHL=false).",
            "enum": ["0", "1", "2", "3", "4", "5", "999"]
          },
          "options": {
            "type": "array",
            "description": "Array of answer options (only applies when isHL=false).",
            "items": {
              "type": "object",
              "properties": {
                "content": {
                  "type": "string",
                  "description": "Content of the option"
                },
                "isAnswer": {
                  "type": "boolean",
                  "description": "Whether this option is correct"
                },
                "optionLabel": {
                  "type": "string",
                  "description": "Label for the option (A, B, C, D, etc.)",
                  "pattern": "^[A-Z]$"
                },
                "index": {
                  "type": "integer",
                  "description": "Index of the option",
                  "minimum": 0
                }
              },
              "required": [
                  "content",
                  # "isAnswer",
                  # "optionLabel",
                  "index"
              ]
            },
            "minItems": 1
          }
        },
        "required": [
          "isHL",
          "content",
          "index"
        ]
      }
    }
  },
  "required": [
    "questions"
  ]
}