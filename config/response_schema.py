ARRAY_BASED_SCHEMA={
  "type": "object",
  "description": "Schema for quiz questions with support for accompanying learning materials.",
  "properties": {
    "materials": {
      "type": "array",
      "description": "Array of learning materials (passages, images, etc.). Each material has an 'id' that questions can reference.",
      "items": {
        "type": "object",
        "properties": {
          "id": {
            "type": "string",
            "description": "A unique identifier for the material. This ID is used in the 'materialRef' field of a question."
          },
          "content": {
            "type": "string",
            "description": "The content of the material (e.g., a text passage, HTML code, or a URL to an image/audio file)."
          }
        },
        "required": [
          "id",
          "content"
        ]
      }
    },
    "questions": {
      "type": "array",
      "description": "Array of questions.",
      "items": {
        "type": "object",
        "properties": {
          "content": {
            "type": "string",
            "description": "The content (text/HTML) of the question."
          },
          "indexPart": {
            "type": "integer",
            "description": "The index identifying the quiz section this question belongs to start with 0",
            "minimum": 0
          },
          "explainQuestion": {
            "type": "string",
            "description": "A detailed explanation for the question."
          },
          "isExplain": {
            "type": "boolean",
            "description": "Whether the explanation should be displayed."
          },
          "mappingScore": {
            "type": "object",
            "description": "An object for mapping scores based on different criteria."
          },
          "optionAnswer": {
            "type": "array",
            "description": "An array containing the indices of the correct answers.",
            "items": {
              "type": "integer"
            }
          },
          "numberId": {
            "type": "integer",
            "description": "Question number identifier",
            "minimum": 1
          },
          "scores": {
            "type": "number",
            "description": "The score for this question."
          },
          "totalOption": {
            "type": "integer",
            "description": "The total number of options for the question."
          },
          "typeAnswer": {
            "type": "string",
             "description": "Type of answer: 0=Multiple choice single answer, 1=Multiple choice multiple answers, 2=Fill-in-the-blank essay, 3=Essay, 4=Essay single answer, 5=Essay multiple answers with order, 999=Undefined",
            "enum": ["0", "1", "2", "3", "4", "5", "999"]
          },
          "materialRef": {
            "type": "string",
            "description": "A reference to the 'id' of a material in the 'materials' array if this question is based on a learning material."
          },
          "options": {
            "type": "array",
            "description": "Array of answer options.",
            "items": {
              "type": "object",
              "properties": {
                "content": {
                  "type": "string",
                  "description": "The content of the option."
                },
                "isAnswer": {
                  "type": "boolean",
                  "description": "Whether this is a correct answer."
                },
                "optionLabel": {
                  "type": "string",
                  "description": "The label for the option (A, B, C, D)."
                }
              },
              "required": [
                "content"
              ]
            }
          }
        },
        "required": [
          "content",
          "indexPart"
        ]
      }
    }
  },
  "required": [
    "questions"
  ]
}