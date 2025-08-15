ARRAY_BASED_SCHEMA={
  "type": "object",
  "description": "Schema for quiz questions with support for accompanying learning materials.",
  "properties": {
    # "materials": {
    #   "type": "array",
    #   "description": "Array of learning materials (passages, images, etc.). Each material has an 'id' that questions can reference.",
    #   "items": {
    #     "type": "object",
    #     "properties": {
    #       "id": {
    #         "type": "string",
    #         "description": "A unique identifier for the material. This ID is used in the 'materialRef' field of a question."
    #       },
    #       "content": {
    #         "type": "string",
    #         "description": "The content of the material (e.g., a text passage, HTML code, or a URL to an image/audio file)."
    #       }
    #     },
    #     "required": [
    #       "id",
    #       "content"
    #     ]
    #   }
    # },
    "quizParts": {
      "type": "array",
      "description": "Một mảng chứa các phần của bài thi. Mỗi phần có thông tin riêng và danh sách câu hỏi của nó.",
      "items": {
        "type": "object",
        "properties": {
          "sectionIndex": {
            "type": "integer",
            "description": "section Index start from 0.",
            "minimum": 0
          },
          "sectionTitle": {
            "type": "string",
            "description": "The title (text/HTML) of this sectionTitle."
          },
          "sectionDescription": {
            "type": "string",
            "description": "description of thí section, you will generate this"
          },
          "maxScore": {
            "type": "integer",
            "description": "Điểm tối đa cho phần này.",
            "minimum": 0
          },
        "questions": {
          "type": "array",
          "description": "Array of questions belong to this section.",
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
                "description": "extract explanation from context related to the question"
              },
              "isExplain": {
                "type": "boolean",
                "description": "Whether the explanation should be displayed."
              },
              "numberId": {
                "type": "integer",
                "description": "Question number identifier in the question",
                "minimum": 1
              },
              "optionAnswer": {
                "type": "array",
                "description": "Extraction the indices/boolean values of the correct answers  .ex true/false type question ['true', 'false', 'false', 'true'], mutiple choice question[1,2,3]",
                "items": {}
              },
              "totalOption": {
                "type": "integer",
                "description": "The total number of options for the question."
              },
              "typeAnswer": {
                "type": "string",
                "description": "Type of answer,you rely on the question content to get get this: 0=Multiple choice single answer, 1=Multiple choice multiple answers, 2=Fill-in-the-blank essay, 3=Essay, 4=Essay single answer, 5=Essay multiple answers with order, 999=Undefined",
                "enum": ["0", "1", "2", "3", "4", "5", "999"]
              },
              # "materialRef": {
              #   "type": "string",
              #   "description": "A reference to the 'id' of a material in the 'materials' array if this question is based on a learning material."
              # },
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
              "typeAnswer",
              "indexPart"
            ]
          }
        }
      },
      "required": [
        "questions"
      ]
 }
    }
  },
  "required": [
    "quizParts"
  ]
}
AI_ANSWER_GEN = {
    "type": "object",
    "properties": {
        "optionAnswer": { 
            "type": "array",
            "description": "this is not answer, this is array containing the indices of the correct answers if we need true/false type answer ['true', 'false', 'false', 'true'], mutiple choice answer[1,2,3]",
            "items": {}
        },
        "totalOption": {
            "type": "integer",
            "description": "The total number of options for the question."
        },
        "explainQuestion": {
            "type": "string",
            "description": "A detail explanation why the answer is the correct answer, should use Vietnamese if possible"
        },
        "options": {
            "type": "array",
            "description": "An array of answer choices. For multiple-choice questions, list all options. For free-response questions, this array must contain ONLY ONE object where 'content' is the final answer from 'explainQuestion', isAnswer is true",
            # "minItems": 1,
            "items": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The content of the option."
                    },
                    "isAnswer": {
                        "type": "boolean",
                        "description": "Whether this is a correct answer. "
                    },
                   
                },
                "required": [
                    "content",
                    "isAnswer",
                  
                ] 
            }
        },
        
    },
    "required": [
        "explainQuestion",
        "optionAnswer",
        "totalOption",
        "options"
    ]
}