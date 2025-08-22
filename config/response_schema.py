ARRAY_BASED_SCHEMA = {
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
          "startIndex": {
            "type": "integer",
            "description": "Chỉ mục bắt đầu của nội dung tài liệu trong tệp Markdown gốc."
          },
          "endIndex": {
            "type": "integer",
            "description": "Chỉ mục kết thúc của nội dung tài liệu trong tệp Markdown gốc."
          }
        },
        "required": [
          "id",
          "startIndex",
          "endIndex"
        ]
      }
    },
    "sections": {
      "type": "array",
      "description": "Array of sections/chapters organizing the quiz questions.",
      "items": {
        "type": "object",
        "properties": {
          "sectionTitle": {
            "type": "string",
            "description": "Title of the section, without the numbering part in the section title, ex. (Câu trắc nghiệm nhiều phương án lựa chọn...')."
          },
          "questions": {
            "type": "array",
            "description": "Array of questions belonging to this section.",
            "items": {
              "type": "object",
              "properties": {
                "startIndex": {
                  "type": "integer",
                  "description": "Chỉ mục bắt đầu của nội dung câu hỏi trong tệp Markdown gốc."
                },
                "endIndex": {
                  "type": "integer",
                  "description": "Chỉ mục kết thúc của nội dung câu hỏi trong tệp Markdown gốc."
                },
                "typeAnswer": {
                  "type": "string",
                  "description": "Type of answer, you rely on the question content to get this: 0=Multiple choice single answer, 1=Multiple choice multiple answers, 2=Fill-in-the-blank essay, 3=Essay, 4=Essay single answer, 5=Essay multiple answers with order,6=True/False question, 999=Undefined",
                  "enum": [
                    "0",
                    "1",
                    "2",
                    "3",
                    "4",
                    "5",
                    "6",
                    "999"
                  ]
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
                  "type": "string"
                },
                "options": {
                  "anyOf": [
                    {
                      "type": "array",
                      "items": {
                        "type": "object",
                        "properties": {
                          "startIndex": {
                            "type": "integer",
                            "description": "Chỉ mục bắt đầu của nội dung lựa chọn trong tệp Markdown gốc."
                          },
                          "endIndex": {
                            "type": "integer",
                            "description": "Chỉ mục kết thúc của nội dung lựa chọn trong tệp Markdown gốc."
                          },
                          "isAnswer": {
                            "type": "boolean",
                            "description": "Whether the option is the correct answer."
                          },
                          "optionLabel": {
                            "type": "string"
                          }
                        },
                        "required": [
                          "startIndex",
                          "endIndex"
                        ]
                      }
                    },
                    {
                      "type": "array",
                      "description": "for typeAnswer='5','4','3', Array with only one option to show the answer.",
                      "items": {
                        "type": "object",
                        "properties": {
                          "startIndex": {
                            "type": "integer",
                            "description": "Chỉ mục bắt đầu của nội dung câu trả lời cuối cùng trong tệp Markdown gốc."
                          },
                          "endIndex": {
                            "type": "integer",
                            "description": "Chỉ mục kết thúc của nội dung câu trả lời cuối cùng trong tệp Markdown gốc."
                          },
                          "isAnswer": {
                            "type": "boolean",
                            "description": "default is true",
                            "default": True
                          },
                          "optionLabel": {
                            "type": "string",
                            "description": "default is A",
                            "default": "A"
                          }
                        },
                        "required": [
                          "startIndex",
                          "endIndex",
                          "isAnswer",
                          "optionLabel"
                        ]
                      }
                    }
                  ]
                }
              },
              "required": [
                "startIndex",
                "endIndex",
                "typeAnswer",
                "correctOption",
                "options"
              ]
            }
          }
        },
        "required": [
          "sectionTitle",
          # "sectionDescription",
          "questions",
          # "maxScore"
        ]
      }
    }
  },
  "required": [
    "sections"
  ]
}