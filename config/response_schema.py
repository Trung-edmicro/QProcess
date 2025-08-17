ARRAY_BASED_SCHEMA=ARRAY_BASED_SCHEMA = {
  "type": "object",
  "description": "Schema for quiz questions with support for accompanying learning materials and sections.",
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
    "sections": {
      "type": "array",
      "description": "Array of sections/chapters organizing the quiz questions.",
      "items": {
        "type": "object",
        "properties": {
          # "sectionIndex": {
          #   "type": "integer",
          #   "description": "Index of the section (0-based ordering).",
          #   "minimum": 0
          # },
          "sectionTitle": {
            "type": "string",
            "description": "Title of the section , without the numbering part in the section title, ex. (Câu trắc nghiệm nhiều phương án lựa chọn...')."
          },
          "sectionDescription": {
            "type": "string",
            "description": "Ai generated description or instructions for the section base on the content."
          },
          "maxScore": {
            "type": "number",
            "description": "Maximum score possible for this section."
          },
          "questions": {
            "type": "array",
            "description": "Array of questions belonging to this section.",
            "items": {
              "type": "object",
              "properties": {
                "content": {
                  "type": "string",
                  "description": "The content (text/HTML) of the question,remove numbering part in the content."
                },
                "explainQuestion": {
                  "type": "string",
                  "description": "A detail explanation why the answer is the correct answer, should use Vietnamese if possible"
                },
                # "isExplain": {
                #   "type": "boolean",
                #   "description": "Whether the explanation should be displayed."
                # },
                # "numberId": {
                #   "type": "integer",
                #   "description": "Question number identifier in the question.",
                #   "minimum": 1
                # },
                # "totalOption": {
                #   "type": "integer",
                #   "description": "The total number of options for the question."
                # },
                "typeAnswer": {
                  "type": "string",
                  "description": "Type of answer, you rely on the question content to get this: 0=Multiple choice single answer, 1=Multiple choice multiple answers, 2=Fill-in-the-blank essay, 3=Essay, 4=Essay single answer, 5=Essay multiple answers with order,6=True/False question, 999=Undefined",
                  "enum": ["0", "1", "2", "3", "4", "5","6", "999"]
                },
                "correctOption": {
                  "anyOf": [
                    {
                      "type": "array",
                      "description": "For typeAnswer='6', True/False questions - array of boolean values for individual statements to evaluate etc. Example: [true, false, false, true]",
                      "items": {
                        "type": "boolean"
                      },
                      "minItems": 1
                    },
                    {
                      "type": "array", 
                      "description": "For typeAnswer='0','1', Single or Multiple choice questions - array of integer indices of correct answers (0-based). Can be single answer [1] or multiple answers [0, 2, 3].",
                      "items": {
                        "type": "integer",
                        "minimum": 0
                      },
                      "minItems": 1
                    },
                    {
                      "type": "array",
                      "description": "for typeAnswer='5','4','3', Last answer for the questions.",
                      "maxItems": 0
                    }
                  ]
                },
                "materialRef": {
                  "type": "string",
                  "description": "A reference to the 'id' of a material in the 'materials' array if this question is based on a learning material."
                },
                "options": {
                  "anyOf": [
                    { "type": "array",
                      "description": "Array of answer options.",
                      "items": {
                        "type": "object",
                        "properties": {
                          "content": {
                            "type": "string",
                            "description": "The content (text/HTML) of the option."
                          },
                          "isAnswer": {
                            "type": "boolean",
                            "description": "Whether the option is the correct answer."
                          },
                          "optionLabel": {
                            "type": "string",
                            "description": "The label for the option (A, B, C, D)."
                          }
                        },
                        "required": [
                          "content"
                        ]
                      }},
                      {"type": "array",
                        "description": "for typeAnswer='5','4','3', Array with only one option to show the answer.",
                        "items": {
                          "type": "object",
                          "properties": {
                            "content": {
                              "type": "string",
                              "description": "The short content  (text/HTML) of the last answer."
                            },
                            "isAnswer":{  "type": "boolean",
                                          "description": "default is true",
                                          "default": True},
                            "optionLabel":{  "type": "string",
                                              "description": "default is A",
                                              "default": "A"}
                          },
                          "required": [
                            "content",
                            "isAnswer",
                            "optionLabel"
                          ]
                  }}
                  ]
                  
                }
              },
              "required": [
                "content",
                "typeAnswer",
                "explainQuestion",
                # "isExplain",
                # "numberId",
                # "totalOption",
                "correctOption",
                "options"
              ]
            }
          }
        },
        "required": [
          # "sectionIndex",
          "sectionTitle",
          "sectionDescription",
          "questions",
          "maxScore"
        ]
      }
    }
  },
  "required": ["sections"]
}